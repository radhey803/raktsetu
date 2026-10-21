"""
Medical Rules & Compatibility Engine
====================================
Loads official guidelines from data/medical_rules.json (WHO, NBTC India, Red Cross).
Enforces:
- Red Cell Compatibility Matrix (Recipient group -> List of Compatible Donor groups)
- Bombay Phenotype (Oh) isolation
- Donor eligibility criteria & minimum donation intervals
- Mandatory disclaimer: "Guidance only, not medical advice. Confirm with a doctor or blood bank."
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

RULES_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "medical_rules.json"


def load_medical_rules() -> Dict[str, Any]:
    """Loads medical rules config file."""
    if not RULES_PATH.exists():
        raise FileNotFoundError(f"Medical rules file missing at: {RULES_PATH}")
    with open(RULES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


_RULES_CACHE: Optional[Dict[str, Any]] = None


def get_rules() -> Dict[str, Any]:
    global _RULES_CACHE
    if _RULES_CACHE is None:
        _RULES_CACHE = load_medical_rules()
    return _RULES_CACHE


def get_compatible_donor_groups(patient_group: str) -> Tuple[List[str], Optional[str], str]:
    """
    Returns (compatible_donor_groups, clinical_warning, source_citation).
    patient_group must be one of:
    'O-', 'O+', 'A-', 'A+', 'B-', 'B+', 'AB-', 'AB+', 'Bombay (Oh+)', 'Bombay (Oh-)'
    """
    rules = get_rules()
    compat = rules.get("compatibility", {}).get("red_cells", {})

    clean_grp = patient_group.strip()
    # Normalize common variations
    norm_map = {
        "o-": "O-",
        "o+": "O+",
        "a-": "A-",
        "a+": "A+",
        "b-": "B-",
        "b+": "B+",
        "ab-": "AB-",
        "ab+": "AB+",
        "bombay": "Bombay (Oh+)",
        "bombay (oh+)": "Bombay (Oh+)",
        "bombay (oh-)": "Bombay (Oh-)",
        "oh+": "Bombay (Oh+)",
        "oh-": "Bombay (Oh-)",
    }
    canonical = norm_map.get(clean_grp.lower(), clean_grp)

    rule = compat.get(canonical)
    if not rule:
        # Fallback to exact match only if unverified
        return [canonical], "Group not in standard ABO/Rh table. Verify with blood bank.", "TODO_VERIFY"

    compatible_groups: List[str] = rule["compatible_donor_groups"]
    warning: Optional[str] = None

    if "Bombay" in canonical:
        warning = (
            "CRITICAL BOMBAY: Bombay Blood Group lacks the H-antigen and can ONLY receive Bombay Blood Group units. "
            "Transfusion of standard O, A, B, or AB blood is lethal."
        )
    elif canonical.endswith("-"):
        warning = f"Rh-Negative Protocol: {canonical} is Rh-negative. Red blood cells must be Rh-negative to prevent anti-D alloimmunization."

    source = f"{rule.get('source', 'NBTC India')} ({rule.get('source_url', '')})"
    return compatible_groups, warning, source


def get_compatible_groups(patient_group: str) -> List[str]:
    """Returns only the list of compatible donor groups for a given recipient group."""
    groups, _, _ = get_compatible_donor_groups(patient_group)
    return groups


def is_rh_negative(blood_group: str) -> bool:
    """Returns True if the blood group is Rh-negative (and not Bombay)."""
    grp = blood_group.strip()
    return grp.endswith("-") and "Bombay" not in grp and "Oh" not in grp


def is_bombay_phenotype(blood_group: str) -> bool:
    """Returns True if the blood group is Bombay (Oh) phenotype."""
    grp = blood_group.strip().lower()
    return "bombay" in grp or "oh" in grp


def get_emergency_clinical_warning(blood_group: str) -> Optional[str]:
    """Returns clinical alert for emergency mode if Rh-negative or Bombay."""
    _, warning, _ = get_compatible_donor_groups(blood_group)
    return warning


def get_medical_disclaimer() -> str:
    """Returns official disclaimer from medical rules config."""
    rules = get_rules()
    return rules.get("disclaimer", "Guidance only, not medical advice. Confirm with a doctor or blood bank.")


def get_source_attribution() -> str:
    """Returns primary source attribution from medical rules config."""
    rules = get_rules()
    return rules.get("sources", {}).get("primary_india", "National Blood Transfusion Council (NBTC), MoHFW India")


def get_donor_eligibility_criteria() -> Dict[str, Any]:
    """Returns donor selection questionnaire and rules."""
    rules = get_rules()
    return rules.get("donor_eligibility", {})
