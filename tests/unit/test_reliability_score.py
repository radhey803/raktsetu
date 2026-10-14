"""
Unit Tests: Facility Reliability Score
======================================
Validates the mathematical scoring contract (0 - 100 points):
1. Freshness: 50 pts
2. Valid Contact: 25 pts
3. Component Completeness: 25 pts
"""

import pytest


def calculate_reliability_score(
    days_since_update: int,
    has_valid_phone: bool,
    has_address: bool,
    distinct_components_count: int
) -> tuple[int, str]:
    # 1. Freshness Points (0-50)
    if days_since_update <= 1:
        freshness = 50
    elif days_since_update <= 7:
        freshness = 35
    elif days_since_update <= 30:
        freshness = 15
    else:
        freshness = 0

    # 2. Contact Points (0-25)
    if has_valid_phone:
        contact = 25
    elif has_address:
        contact = 10
    else:
        contact = 0

    # 3. Component Completeness Points (0-25)
    if distinct_components_count >= 3:
        completeness = 25
    elif distinct_components_count >= 1:
        completeness = 15
    else:
        completeness = 0

    total_score = freshness + contact + completeness
    if total_score >= 75:
        tier = "HIGH"
    elif total_score >= 50:
        tier = "MODERATE"
    else:
        tier = "LOW"

    return total_score, tier


def test_perfect_reliability_score():
    score, tier = calculate_reliability_score(
        days_since_update=0,
        has_valid_phone=True,
        has_address=True,
        distinct_components_count=4
    )
    assert score == 100
    assert tier == "HIGH"


def test_stale_data_score_penalty():
    score, tier = calculate_reliability_score(
        days_since_update=45,
        has_valid_phone=True,
        has_address=True,
        distinct_components_count=3
    )
    # 0 freshness + 25 contact + 25 completeness = 50
    assert score == 50
    assert tier == "MODERATE"


def test_critically_unreliable_facility():
    score, tier = calculate_reliability_score(
        days_since_update=90,
        has_valid_phone=False,
        has_address=False,
        distinct_components_count=0
    )
    assert score == 0
    assert tier == "LOW"
