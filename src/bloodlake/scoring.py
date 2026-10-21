"""
Facility Data Reliability Score (0 - 100)
=========================================
Calculates objective credibility rating across three pillars:
1. Freshness Score (50 pts max):
   - updated < 24h (<= 1 day): 50 pts
   - updated < 3d (2-3 days): 35 pts
   - updated < 7d (4-6 days): 20 pts
   - updated < 14d (7-13 days): 8 pts
   - older (>= 14 days or None): 0 pts
2. Valid Contact (25 pts max):
   - phone number passes format check (>= 8 numeric digits): 25 pts
   - else: 0 pts
3. Component Completeness (25 pts max):
   - >= 3 distinct blood components: 25 pts
   - 1 or 2 components: 15 pts
   - 0: 0 pts

Reliability Labels:
- High: score >= 75
- Medium: score between 40 and 74
- Low: score < 40
"""

import re
from typing import Optional, Tuple


def calculate_reliability_score(
    days_since_update: Optional[int],
    phone: Optional[str] = None,
    has_valid_phone: Optional[bool] = None,
    distinct_components_count: int = 0,
) -> Tuple[int, str]:
    """
    Computes (score, label) for a facility.
    Score range: 0 to 100.
    Label: 'High', 'Medium', or 'Low'.
    """
    # 1. Freshness (50 pts)
    if days_since_update is None or days_since_update < 0:
        freshness = 0
    elif days_since_update <= 1:
        freshness = 50
    elif days_since_update <= 3:
        freshness = 35
    elif days_since_update <= 6:
        freshness = 20
    elif days_since_update <= 13:
        freshness = 8
    else:
        freshness = 0

    # 2. Contact Verification (25 pts)
    if has_valid_phone is not None:
        valid_contact = has_valid_phone
    elif phone:
        digits = re.findall(r"\d", phone)
        valid_contact = len(digits) >= 8
    else:
        valid_contact = False

    contact = 25 if valid_contact else 0

    # 3. Component Completeness (25 pts)
    if distinct_components_count >= 3:
        completeness = 25
    elif distinct_components_count >= 1:
        completeness = 15
    else:
        completeness = 0

    total_score = freshness + contact + completeness

    if total_score >= 75:
        label = "High"
    elif total_score >= 40:
        label = "Medium"
    else:
        label = "Low"

    return total_score, label
