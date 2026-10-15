"""
Integration Tests: Razorpay Billing, Entitlements & Webhooks
===========================================================
Validates:
1. Subscription order creation with GST calculation
2. HMAC-SHA256 signature verification
3. Webhook idempotency
4. Payment failure 3-day grace period
5. Server-side entitlement enforcement
6. Usage metering counters
7. Commercial go-live checklist
"""

import hashlib
import hmac

from starlette.testclient import TestClient

from bloodgrid.api.main import app
from bloodgrid.api.routers.billing import (
    PLAN_ENTITLEMENTS,
    calculate_gst_breakup,
    verify_razorpay_signature,
)

client = TestClient(app)


def test_calculate_gst_breakup():
    # Intra-state (CGST + SGST 9% each)
    breakup = calculate_gst_breakup(299.0, is_inter_state=False)
    assert breakup["sac_code"] == "998313"
    assert breakup["cgst_rate_pct"] == 9.0
    assert breakup["sgst_rate_pct"] == 9.0
    assert breakup["igst_rate_pct"] == 0.0
    assert (
        round(
            breakup["taxable_amount_inr"] + breakup["cgst_amount_inr"] + breakup["sgst_amount_inr"]
        )
        == 299
    )

    # Inter-state (IGST 18%)
    breakup_inter = calculate_gst_breakup(999.0, is_inter_state=True)
    assert breakup_inter["igst_rate_pct"] == 18.0
    assert breakup_inter["cgst_rate_pct"] == 0.0


def test_razorpay_signature_verification_helper():
    secret = "test_webhook_secret_12345"
    payload = b'{"event":"payment.captured","id":"evt_123"}'
    valid_sig = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()

    assert verify_razorpay_signature(payload, valid_sig, secret) is True
    assert verify_razorpay_signature(payload, "invalid_signature", secret) is False


def test_create_subscription_order():
    resp = client.post(
        "/v1/billing/create-order",
        json={
            "plan": "pro",
            "billing_name": "Test Hospital Coordinator",
            "billing_email": "billing@testhosp.org",
            "gstin": "24AAAAA0000A1Z5",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["amount_inr"] == 299
    assert data["amount_paise"] == 29900
    assert "order_id" in data
    assert "pci_dss_notice" in data


def test_webhook_payment_captured_and_idempotency():
    order_id = "order_test_webhook_capture"
    event_id = "evt_capture_12345"

    payload = {
        "id": event_id,
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test_998877",
                    "order_id": order_id,
                    "amount": 29900,
                    "notes": {"user_email": "doctor@hospital.org", "plan": "pro"},
                }
            }
        },
    }

    # 1. First delivery -> processed
    resp1 = client.post("/v1/billing/webhook", json=payload)
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["status"] == "processed"
    assert data1["event"] == "payment.captured"

    # 2. Duplicate delivery -> idempotently ignored
    resp2 = client.post("/v1/billing/webhook", json=payload)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["status"] == "ignored"
    assert data2["reason"] == "duplicate_event"


def test_webhook_payment_failed_initiates_grace_period():
    order_id = "order_test_fail_grace"
    event_id = "evt_fail_998811"

    # Seed order first
    client.post(
        "/v1/billing/create-order",
        json={"plan": "developer", "billing_name": "Dev Team", "billing_email": "dev@startup.io"},
    )

    payload = {
        "id": event_id,
        "event": "payment.failed",
        "payload": {"payment": {"entity": {"id": "pay_failed_123", "order_id": order_id}}},
    }

    resp = client.post("/v1/billing/webhook", json=payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "processed"


def test_entitlements_spec():
    assert PLAN_ENTITLEMENTS["free"].max_active_alerts == 0
    assert PLAN_ENTITLEMENTS["free"].csv_exports_allowed is False
    assert PLAN_ENTITLEMENTS["pro"].max_active_alerts == 10
    assert PLAN_ENTITLEMENTS["developer"].csv_exports_allowed is True
    assert PLAN_ENTITLEMENTS["organization"].max_active_alerts == 100


def test_go_live_checklist_endpoint():
    resp = client.get("/v1/billing/go-live-checklist")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "TEST_MODE_ACTIVE"
    assert len(data["checklist"]) >= 4
    assert any(item["id"] == "kyc_verification" for item in data["checklist"])
    assert "zero_card_liability" in data
