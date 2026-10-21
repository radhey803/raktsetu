"""
Unit Tests: Stock Change Deltas, Risk Rules & Anomaly Detection
==============================================================
Validates Phase 5 requirements:
- delta vs previous snapshot
- 7-day delta (only when >= 7 real snapshot dates exist)
- rule-based risk flag 'Falling' when stock decreased across 3 consecutive snapshot intervals (needs >= 4 snapshots)
- anomaly flag 'SUDDEN_DROP_TO_ZERO' when positive stock abruptly falls to zero
"""

from typing import List, Optional, Tuple


def evaluate_stock_change_and_risk(
    history_units_chronological: List[int],
    total_distinct_dates: int,
) -> Tuple[Optional[int], Optional[int], str, str]:
    """
    Pure Python implementation of mart_stock_change logic for unit testing:
    Input: history_units_chronological in ASCENDING date order [u_oldest, ..., u_latest]
    Returns: (delta_prev, delta_7d, risk_flag, anomaly_flag)
    """
    if not history_units_chronological:
        return None, None, "Stable", "NORMAL"

    current = history_units_chronological[-1]
    prev = history_units_chronological[-2] if len(history_units_chronological) >= 2 else None

    # 1. Delta vs previous
    delta_prev = (current - prev) if prev is not None else None

    # 2. 7-Day Delta (requires at least 7 distinct snapshot dates)
    if total_distinct_dates >= 7 and len(history_units_chronological) >= 7:
        delta_7d = current - history_units_chronological[-7]
    else:
        delta_7d = None

    # 3. Rule-based risk flag:
    # 'Falling' if decreased in 3 consecutive intervals (needs >= 4 snapshots: u[-4] > u[-3] > u[-2] > u[-1])
    if len(history_units_chronological) >= 4:
        u1, u2, u3, u4 = (
            history_units_chronological[-4],
            history_units_chronological[-3],
            history_units_chronological[-2],
            history_units_chronological[-1],
        )
        if u4 < u3 < u2 < u1:
            risk_flag = "Falling"
        elif u4 <= 2:
            risk_flag = "Depleted"
        else:
            risk_flag = "Stable"
    elif current <= 2:
        risk_flag = "Depleted"
    else:
        risk_flag = "Stable"

    # 4. Anomaly detection: Sudden drop to zero from positive level
    if prev is not None and prev > 0 and current == 0:
        anomaly_flag = "SUDDEN_DROP_TO_ZERO"
    else:
        anomaly_flag = "NORMAL"

    return delta_prev, delta_7d, risk_flag, anomaly_flag


def test_single_snapshot_has_no_deltas():
    # Only 1 snapshot date exists
    delta_prev, delta_7d, risk, anomaly = evaluate_stock_change_and_risk([15], total_distinct_dates=1)
    assert delta_prev is None
    assert delta_7d is None
    assert risk == "Stable"
    assert anomaly == "NORMAL"


def test_delta_vs_previous():
    # Snapshot on day 1: 20 units; Day 2: 14 units
    delta_prev, delta_7d, risk, anomaly = evaluate_stock_change_and_risk([20, 14], total_distinct_dates=2)
    assert delta_prev == -6
    assert delta_7d is None  # Only 2 dates, needs >= 7
    assert risk == "Stable"
    assert anomaly == "NORMAL"


def test_falling_risk_flag_three_consecutive_decreases():
    # 4 snapshots with strict decrease: 25 -> 20 -> 15 -> 8
    delta_prev, delta_7d, risk, anomaly = evaluate_stock_change_and_risk(
        [25, 20, 15, 8], total_distinct_dates=4
    )
    assert delta_prev == -7
    assert risk == "Falling"
    assert anomaly == "NORMAL"


def test_non_falling_when_fluctuating():
    # Decreased, then increased, then decreased: 25 -> 20 -> 22 -> 18 (Not strictly falling across 3 intervals)
    delta_prev, delta_7d, risk, anomaly = evaluate_stock_change_and_risk(
        [25, 20, 22, 18], total_distinct_dates=4
    )
    assert delta_prev == -4
    assert risk == "Stable"


def test_anomaly_sudden_drop_to_zero():
    # Previous was 18, now suddenly 0
    delta_prev, delta_7d, risk, anomaly = evaluate_stock_change_and_risk([18, 0], total_distinct_dates=2)
    assert delta_prev == -18
    assert anomaly == "SUDDEN_DROP_TO_ZERO"
    assert risk == "Depleted"


def test_7d_delta_calculated_when_sufficient_dates():
    # 7 snapshot intervals
    history = [30, 28, 25, 24, 20, 18, 14]
    delta_prev, delta_7d, risk, anomaly = evaluate_stock_change_and_risk(history, total_distinct_dates=7)
    assert delta_prev == -4
    assert delta_7d == 14 - 30  # -16 units over 7 days
    assert risk == "Falling"
