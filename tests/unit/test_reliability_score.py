"""
Unit Tests: Facility Reliability Score & Boundary Cases
=======================================================
Phase 1 Requirements:
- Freshness (50 pts): <24h=50, <3d=35, <7d=20, <14d=8, older=0
- Valid contact (25 pts): phone format check (>= 8 digits)
- Completeness (25 pts): share of expected components (>=3 is 25, 1-2 is 15, 0 is 0)
- Labels: High >= 75, Medium 40-74, Low < 40
"""

import pytest

from bloodlake.scoring import calculate_reliability_score


def test_perfect_reliability_score():
    score, label = calculate_reliability_score(
        days_since_update=0, phone="02692-223344", distinct_components_count=4
    )
    assert score == 100
    assert label == "High"


@pytest.mark.parametrize(
    "days, expected_freshness",
    [
        (0, 50),
        (1, 50),
        (2, 35),
        (3, 35),
        (4, 20),
        (6, 20),
        (7, 8),
        (13, 8),
        (14, 0),
        (30, 0),
        (None, 0),
    ],
)
def test_freshness_boundaries(days, expected_freshness):
    # Without phone and components, score is solely freshness
    score, _ = calculate_reliability_score(
        days_since_update=days, phone=None, distinct_components_count=0
    )
    assert score == expected_freshness


@pytest.mark.parametrize(
    "phone, expected_contact",
    [
        ("9825012345", 25),  # 10 digits
        ("02692-223344", 25),  # 11 digits formatted
        ("12345678", 25),  # exactly 8 digits
        ("1234567", 0),  # 7 digits (too short)
        ("Phone: -", 0),  # invalid text
        ("", 0),  # empty
        (None, 0),  # none
    ],
)
def test_contact_boundaries(phone, expected_contact):
    score, _ = calculate_reliability_score(
        days_since_update=30, phone=phone, distinct_components_count=0
    )
    assert score == expected_contact


@pytest.mark.parametrize(
    "components, expected_completeness",
    [
        (0, 0),
        (1, 15),
        (2, 15),
        (3, 25),
        (5, 25),
    ],
)
def test_completeness_boundaries(components, expected_completeness):
    score, _ = calculate_reliability_score(
        days_since_update=30, phone=None, distinct_components_count=components
    )
    assert score == expected_completeness


@pytest.mark.parametrize(
    "days, phone, comps, expected_score, expected_label",
    [
        # Boundary: High threshold >= 75
        (0, "9825012345", 3, 100, "High"),  # 50 + 25 + 25 = 100
        (1, "9825012345", 1, 90, "High"),  # 50 + 25 + 15 = 90
        (2, "9825012345", 2, 75, "High"),  # 35 + 25 + 15 = 75 (exact boundary)
        # Boundary: Medium threshold 40-74
        (4, "9825012345", 3, 70, "Medium"),  # 20 + 25 + 25 = 70
        (4, "9825012345", 1, 60, "Medium"),  # 20 + 25 + 15 = 60
        (7, "9825012345", 1, 48, "Medium"),  # 8 + 25 + 15 = 48
        (14, "9825012345", 1, 40, "Medium"),  # 0 + 25 + 15 = 40 (exact boundary)
        # Boundary: Low threshold < 40
        (4, None, 1, 35, "Low"),  # 20 + 0 + 15 = 35
        (7, "9825012345", 0, 33, "Low"),  # 8 + 25 + 0 = 33
        (14, "9825012345", 0, 25, "Low"),  # 0 + 25 + 0 = 25
        (14, None, 1, 15, "Low"),  # 0 + 0 + 15 = 15
        (14, None, 0, 0, "Low"),  # 0 + 0 + 0 = 0
    ],
)
def test_label_classification_boundaries(days, phone, comps, expected_score, expected_label):
    score, label = calculate_reliability_score(
        days_since_update=days, phone=phone, distinct_components_count=comps
    )
    assert score == expected_score
    assert label == expected_label
