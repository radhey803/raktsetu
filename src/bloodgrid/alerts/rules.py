"""
BloodGrid Alert Rules Engine
============================
Defines notification trigger rules:
1. AVAILABILITY_SURGE: "Notify when O- PRBC becomes available in Anand"
2. DEFICIT_ALERT: "Notify when district inventory drops below N units"

Guards:
- Deduplication (prevents re-alerting on the same facility stock condition within 24h)
- Quiet Hours (respects 22:00 - 07:00 IST unless flagged as life-critical emergency)
- Rate cap (maximum 5 alerts per subscription per calendar day)
- Cryptographic unsubscribe tokens
"""

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from bloodgrid.config import settings


class AlertSubscription(BaseModel):
    rule_id: str = Field(default_factory=lambda: f"rule_{uuid.uuid4().hex[:10]}")
    user_email: str
    channel: str = Field(default="telegram", description="telegram, email, or webhook")
    telegram_chat_id: Optional[str] = None
    state: str
    district: str
    component: str = "Packed Red Blood Cells"
    blood_group: str = "O-"
    trigger_type: str = Field(default="AVAILABILITY_SURGE", description="AVAILABILITY_SURGE or DEFICIT_ALERT")
    min_units_threshold: int = Field(default=1, ge=0)
    is_emergency: bool = Field(default=False, description="Emergency overrides quiet hours")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True
    alerts_sent_today: int = 0
    max_alerts_per_day: int = 5


def generate_unsubscribe_token(rule_id: str, email: str) -> str:
    """Generates a secure hash token for 1-click unsubscribe links."""
    raw = f"{rule_id}:{email}:{settings.jwt_secret}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def is_in_quiet_hours(dt: Optional[datetime] = None) -> bool:
    """
    Checks if current IST time falls in quiet hours (10:00 PM - 07:00 AM IST).
    UTC is IST - 5:30.
    10:00 PM IST = 16:30 UTC
    07:00 AM IST = 01:30 UTC
    """
    now = dt or datetime.now(timezone.utc)
    # Convert to IST hour
    ist_hour = (now.hour + 5 + (now.minute + 30) // 60) % 24
    return ist_hour >= 22 or ist_hour < 7


def evaluate_alert_rule(
    rule: AlertSubscription,
    available_units: int,
    recent_alert_dispatches: List[Dict[str, Any]]
) -> tuple[bool, Optional[str]]:
    """
    Evaluates an alert subscription against current stock units.
    Returns (should_dispatch, reason).
    """
    if not rule.is_active:
        return False, "Rule is disabled"

    # 1. Rate Cap Guard
    if rule.alerts_sent_today >= rule.max_alerts_per_day:
        return False, f"Daily limit reached ({rule.max_alerts_per_day} alerts/day)"

    # 2. Quiet Hours Guard
    if not rule.is_emergency and is_in_quiet_hours():
        return False, "Suppressed during quiet hours (22:00 - 07:00 IST)"

    # 3. Deduplication Guard: Check if an alert was dispatched for this condition within 24h
    now = datetime.now(timezone.utc)
    for alert in recent_alert_dispatches:
        if alert.get("rule_id") == rule.rule_id:
            dispatched_at = alert.get("dispatched_at")
            if dispatched_at and (now - dispatched_at).total_seconds() < 86400:
                if alert.get("last_units") == available_units:
                    return False, "Deduplicated: Identical stock condition dispatched within 24h"

    # 4. Trigger Conditions
    if rule.trigger_type == "AVAILABILITY_SURGE":
        if available_units >= rule.min_units_threshold:
            return True, f"Stock Surge: {available_units} units now available"
    elif rule.trigger_type == "DEFICIT_ALERT":
        if available_units < rule.min_units_threshold:
            return True, f"Stock Deficit: Units dropped to {available_units}"

    return False, "Trigger conditions not met"
