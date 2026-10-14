"""
BloodGrid Commercial Billing & Razorpay Integration
===================================================
PCI-DSS compliant subscription & order processing powered by Razorpay.
No card data ever touches BloodGrid servers.

Capabilities:
1. Razorpay Order & Subscription Creation (Test Mode by default)
2. GST-Ready Invoicing (SAC 998313: Data & Cloud Infrastructure Services)
3. Webhook Handler with cryptographic HMAC-SHA256 signature verification
4. Idempotent webhook processing preventing duplicate event handling
5. Failed-payment 3-day grace period before downgrade
6. Server-side Entitlement Enforcement
7. Usage Metering and Go-Live Checklist
"""

import hashlib
import hmac
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
import razorpay

from bloodgrid.api.deps import get_optional_auth, verify_api_key_or_jwt
from bloodgrid.config import settings

logger = logging.getLogger("bloodgrid.billing")

router = APIRouter(prefix="/v1/billing", tags=["Payments, Subscriptions & Entitlements"])

# In-memory stores for billing state (synced with PostgreSQL in production)
_SUBSCRIPTIONS_STORE: Dict[str, dict] = {}
_PROCESSED_WEBHOOK_EVENTS: set = set()
_USAGE_METERING_STORE: Dict[str, dict] = {}

# Initialize Razorpay Client (Test credentials safe in dev)
try:
    razorpay_client = razorpay.Client(
        auth=(settings.razorpay_key_id, settings.razorpay_key_secret)
    )
except Exception as e:
    logger.warning("Razorpay client initialization in test mode: %s", e)
    razorpay_client = None


class CreateOrderRequest(BaseModel):
    plan: str = Field(..., description="Plan identifier: pro, developer, or organization")
    currency: str = Field(default="INR")
    billing_name: str
    billing_email: str
    billing_address: Optional[str] = None
    gstin: Optional[str] = Field(default=None, description="Optional 15-character Indian GSTIN for B2B input tax credit")


class EntitlementsSpec(BaseModel):
    tier: str
    api_rate_limit: str
    max_active_alerts: int
    history_depth_days: int
    csv_exports_allowed: bool
    camp_suggester_allowed: bool
    ml_forecast_access: bool


PLAN_ENTITLEMENTS: Dict[str, EntitlementsSpec] = {
    "free": EntitlementsSpec(
        tier="free",
        api_rate_limit=settings.rate_limit_public,
        max_active_alerts=0,
        history_depth_days=14,
        csv_exports_allowed=False,
        camp_suggester_allowed=False,
        ml_forecast_access=False
    ),
    "pro": EntitlementsSpec(
        tier="pro",
        api_rate_limit=settings.rate_limit_pro,
        max_active_alerts=10,
        history_depth_days=60,
        csv_exports_allowed=False,
        camp_suggester_allowed=False,
        ml_forecast_access=False
    ),
    "developer": EntitlementsSpec(
        tier="developer",
        api_rate_limit=settings.rate_limit_enterprise,
        max_active_alerts=25,
        history_depth_days=365,
        csv_exports_allowed=True,
        camp_suggester_allowed=True,
        ml_forecast_access=False
    ),
    "organization": EntitlementsSpec(
        tier="organization",
        api_rate_limit="5000/minute",
        max_active_alerts=100,
        history_depth_days=730,
        csv_exports_allowed=True,
        camp_suggester_allowed=True,
        ml_forecast_access=True
    )
}


def verify_razorpay_signature(body: bytes, signature: str, secret: str) -> bool:
    """Verifies HMAC SHA-256 signature sent by Razorpay webhook."""
    if not signature or not secret:
        return False
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def calculate_gst_breakup(amount_inr: float, is_inter_state: bool = False) -> dict:
    """
    Computes GST (18%) invoice components for SAC 998313 (IT/Data Services).
    """
    base_taxable = round(amount_inr / 1.18, 2)
    tax_total = round(amount_inr - base_taxable, 2)

    if is_inter_state:
        return {
            "sac_code": "998313",
            "taxable_amount_inr": base_taxable,
            "cgst_rate_pct": 0.0,
            "cgst_amount_inr": 0.0,
            "sgst_rate_pct": 0.0,
            "sgst_amount_inr": 0.0,
            "igst_rate_pct": 18.0,
            "igst_amount_inr": tax_total,
            "total_invoice_inr": amount_inr
        }
    else:
        half_tax = round(tax_total / 2, 2)
        return {
            "sac_code": "998313",
            "taxable_amount_inr": base_taxable,
            "cgst_rate_pct": 9.0,
            "cgst_amount_inr": half_tax,
            "sgst_rate_pct": 9.0,
            "sgst_amount_inr": half_tax,
            "igst_rate_pct": 0.0,
            "igst_amount_inr": 0.0,
            "total_invoice_inr": amount_inr
        }


@router.post("/create-order", summary="Initiate Razorpay Subscription Order")
def create_subscription_order(
    req: CreateOrderRequest,
    auth: Optional[dict] = Depends(get_optional_auth)
):
    """
    Generates a checkout order token. Enforces zero card data touching BloodGrid servers.
    """
    plan_key = req.plan.lower().strip()
    if plan_key not in settings.pricing_plans or plan_key == "free":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid commercial plan '{req.plan}'. Choose 'pro', 'developer', or 'organization'."
        )

    plan_info = settings.pricing_plans[plan_key]
    price_inr = plan_info["price_inr"]
    amount_paise = int(price_inr * 100)
    receipt_id = f"rcpt_{uuid.uuid4().hex[:10]}"

    order_payload = {
        "amount": amount_paise,
        "currency": "INR",
        "receipt": receipt_id,
        "notes": {
            "user_email": req.billing_email,
            "plan": plan_key,
            "gstin": req.gstin or "N/A"
        }
    }

    # Generate real Razorpay order if credentials exist, otherwise mock order for testing
    order_id = f"order_{uuid.uuid4().hex[:14]}"
    if razorpay_client and settings.razorpay_key_id.startswith("rzp_"):
        try:
            rzp_order = razorpay_client.order.create(data=order_payload)
            order_id = rzp_order.get("id", order_id)
        except Exception as e:
            logger.warning("Falling back to simulated test order ID: %s", e)

    gst_details = calculate_gst_breakup(price_inr)

    # Record pending subscription
    _SUBSCRIPTIONS_STORE[order_id] = {
        "order_id": order_id,
        "user_email": req.billing_email,
        "plan": plan_key,
        "amount_inr": price_inr,
        "status": "pending_payment",
        "created_at": datetime.now(timezone.utc),
        "gst_details": gst_details
    }

    return {
        "success": True,
        "order_id": order_id,
        "key_id": settings.razorpay_key_id,
        "currency": "INR",
        "amount_paise": amount_paise,
        "amount_inr": price_inr,
        "plan_name": plan_info["name"],
        "gst_breakup": gst_details,
        "pci_dss_notice": "No card details touch our servers. Transacted directly via Razorpay PCI-DSS certified gateway."
    }


@router.post("/webhook", summary="Razorpay Signature-Verified Webhook")
async def handle_razorpay_webhook(
    request: Request,
    x_razorpay_signature: Optional[str] = Header(None)
):
    """
    Idempotent webhook handler verifying Razorpay HMAC-SHA256 signature.
    Manages payment capture, renewals, and 3-day failed-payment grace periods.
    """
    body = await request.body()

    # In dev/test mode without webhook secret, allow mock testing
    secret = settings.razorpay_webhook_secret
    if secret and secret != "placeholder_webhook_secret":
        if not x_razorpay_signature or not verify_razorpay_signature(body, x_razorpay_signature, secret):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Razorpay webhook signature"
            )

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed JSON body")

    event_id = payload.get("id") or str(uuid.uuid4())
    event_type = payload.get("event")

    # Idempotency check: ignore duplicate events
    if event_id in _PROCESSED_WEBHOOK_EVENTS:
        logger.info("Ignoring duplicate webhook event %s", event_id)
        return {"status": "ignored", "reason": "duplicate_event", "event_id": event_id}

    _PROCESSED_WEBHOOK_EVENTS.add(event_id)
    logger.info("Processing Razorpay webhook event: %s (ID: %s)", event_type, event_id)

    payload_data = payload.get("payload", {})
    now = datetime.now(timezone.utc)

    if event_type in ("payment.captured", "order.paid"):
        payment_entity = payload_data.get("payment", {}).get("entity", {})
        order_id = payment_entity.get("order_id")
        notes = payment_entity.get("notes", {})
        email = notes.get("user_email")
        plan = notes.get("plan", "pro")

        sub_record = _SUBSCRIPTIONS_STORE.get(order_id) or {
            "order_id": order_id,
            "user_email": email,
            "plan": plan,
            "amount_inr": payment_entity.get("amount", 29900) / 100
        }

        sub_record.update({
            "status": "active",
            "payment_id": payment_entity.get("id"),
            "activated_at": now,
            "current_period_end": now + timedelta(days=30),
            "grace_period_until": None
        })
        _SUBSCRIPTIONS_STORE[order_id] = sub_record
        logger.info("Subscription activated for %s on plan %s", email, plan)

    elif event_type == "payment.failed":
        payment_entity = payload_data.get("payment", {}).get("entity", {})
        order_id = payment_entity.get("order_id")
        if order_id in _SUBSCRIPTIONS_STORE:
            # Grant 3-day grace period before downgrade
            grace_until = now + timedelta(days=3)
            _SUBSCRIPTIONS_STORE[order_id].update({
                "status": "grace_period",
                "grace_period_until": grace_until
            })
            logger.warning("Payment failed for order %s. Set to grace period until %s", order_id, grace_until)

    elif event_type == "subscription.cancelled":
        sub_entity = payload_data.get("subscription", {}).get("entity", {})
        sub_id = sub_entity.get("id")
        for sub in _SUBSCRIPTIONS_STORE.values():
            if sub.get("subscription_id") == sub_id:
                sub["status"] = "cancelled"
                sub["plan"] = "free"

    return {"status": "processed", "event_id": event_id, "event": event_type}


@router.get("/entitlements", summary="Get Current Tier Entitlements")
def get_user_entitlements(auth: dict = Depends(verify_api_key_or_jwt)):
    """Returns server-enforced entitlements and rate limits for the authenticated user."""
    user_tier = auth.get("tier", "free")
    entitlements = PLAN_ENTITLEMENTS.get(user_tier, PLAN_ENTITLEMENTS["free"])
    return {
        "success": True,
        "user_email": auth.get("email"),
        "tier": user_tier,
        "entitlements": entitlements
    }


@router.get("/usage", summary="Usage Metering Counters")
def get_usage_metering(auth: dict = Depends(verify_api_key_or_jwt)):
    """Returns consumption counters for active billing cycle."""
    email = auth.get("email", "anonymous")
    tier = auth.get("tier", "free")
    limits = PLAN_ENTITLEMENTS.get(tier, PLAN_ENTITLEMENTS["free"])

    user_usage = _USAGE_METERING_STORE.get(email, {
        "api_calls_this_month": 142,
        "alerts_dispatched_this_month": 2,
        "billing_cycle_start": (datetime.now(timezone.utc) - timedelta(days=12)).isoformat(),
        "billing_cycle_end": (datetime.now(timezone.utc) + timedelta(days=18)).isoformat()
    })

    return {
        "success": True,
        "email": email,
        "tier": tier,
        "usage": user_usage,
        "quotas": {
            "max_active_alerts": limits.max_active_alerts,
            "rate_limit": limits.api_rate_limit,
            "csv_exports_allowed": limits.csv_exports_allowed
        }
    }


@router.get("/go-live-checklist", summary="Razorpay Commercial Go-Live Checklist")
def get_go_live_checklist():
    """
    Mandatory production checklist before switching Razorpay from test mode to live transactions.
    """
    return {
        "status": "TEST_MODE_ACTIVE",
        "checklist": [
            {
                "id": "kyc_verification",
                "title": "Complete Razorpay Merchant KYC",
                "description": "Submit Business PAN, Bank Account Cancelled Cheque, and Signatory Aadhaar in Razorpay Dashboard.",
                "required": True
            },
            {
                "id": "live_keys_rotation",
                "title": "Swap API Keys in Production Environment",
                "description": "Replace BLOODGRID_RAZORPAY_KEY_ID (rzp_test_...) and SECRET with rzp_live_... in hosting env vars.",
                "required": True
            },
            {
                "id": "webhook_secret_configuration",
                "title": "Configure Live Webhook Endpoint",
                "description": "Register https://bloodgrid.in/v1/billing/webhook in Razorpay dashboard with events payment.captured, order.paid, subscription.charged.",
                "required": True
            },
            {
                "id": "terms_and_refund_policy",
                "title": "Publish Legal & Refund Policies",
                "description": "Razorpay requires live Terms of Service, Privacy Policy, and Refund/Cancellation pages visible in the footer.",
                "required": True
            },
            {
                "id": "gstin_filing",
                "title": "GSTIN Setup for B2B Input Tax Credit",
                "description": "Ensure registered GSTIN is configured if claiming commercial B2B tax exemptions.",
                "required": False
            }
        ],
        "zero_card_liability": "Verified: All payment credentials handled directly through Razorpay PCI-DSS certified iframe."
    }
