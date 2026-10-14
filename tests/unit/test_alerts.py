"""
Unit Tests: Alert Rules Engine
==============================
Validates notification trigger rules, deduplication, quiet hours suppression,
and daily dispatch limits.
"""

from datetime import datetime, timedelta, timezone
import pytest

from bloodgrid.alerts.rules import (
    AlertSubscription,
    evaluate_alert_rule,
    generate_unsubscribe_token,
    is_in_quiet_hours,
)


def test_availability_surge_triggers():
    rule = AlertSubscription(
        user_email="patient@example.com",
        state="Gujarat",
        district="Anand",
        component="Packed Red Blood Cells",
        blood_group="O-",
        trigger_type="AVAILABILITY_SURGE",
        min_units_threshold=2,
        is_emergency=True  # Bypasses quiet hours
    )

    # When 0 units, should not trigger
    dispatch, reason = evaluate_alert_rule(rule, available_units=0, recent_alert_dispatches=[])
    assert dispatch is False

    # When 3 units, should trigger
    dispatch, reason = evaluate_alert_rule(rule, available_units=3, recent_alert_dispatches=[])
    assert dispatch is True
    assert "Stock Surge" in reason


def test_deficit_alert_triggers():
    rule = AlertSubscription(
        user_email="coordinator@ngo.org",
        state="Gujarat",
        district="Anand",
        trigger_type="DEFICIT_ALERT",
        min_units_threshold=10,
        is_emergency=True
    )

    # When 15 units available, no deficit
    dispatch, reason = evaluate_alert_rule(rule, available_units=15, recent_alert_dispatches=[])
    assert dispatch is False

    # When 4 units available, triggers deficit
    dispatch, reason = evaluate_alert_rule(rule, available_units=4, recent_alert_dispatches=[])
    assert dispatch is True
    assert "Stock Deficit" in reason


def test_daily_rate_cap_enforced():
    rule = AlertSubscription(
        user_email="user@test.com",
        state="Gujarat",
        district="Anand",
        alerts_sent_today=5,
        max_alerts_per_day=5,
        is_emergency=True
    )
    dispatch, reason = evaluate_alert_rule(rule, available_units=10, recent_alert_dispatches=[])
    assert dispatch is False
    assert "Daily limit reached" in reason


def test_deduplication_within_24_hours():
    rule = AlertSubscription(
        rule_id="rule_anand_o_neg",
        user_email="user@test.com",
        state="Gujarat",
        district="Anand",
        is_emergency=True
    )
    recent_dispatches = [
        {
            "rule_id": "rule_anand_o_neg",
            "last_units": 4,
            "dispatched_at": datetime.now(timezone.utc) - timedelta(hours=2)
        }
    ]

    # Same units within 24h -> deduplicated
    dispatch, reason = evaluate_alert_rule(rule, available_units=4, recent_alert_dispatches=recent_dispatches)
    assert dispatch is False
    assert "Deduplicated" in reason


def test_unsubscribe_token_deterministic():
    token1 = generate_unsubscribe_token("rule_123", "user@test.com")
    token2 = generate_unsubscribe_token("rule_123", "user@test.com")
    token_diff = generate_unsubscribe_token("rule_456", "user@test.com")

    assert token1 == token2
    assert token1 != token_diff
    assert len(token1) == 24
