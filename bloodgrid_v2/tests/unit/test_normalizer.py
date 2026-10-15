"""
Unit Tests: Blood Group Normalization
=====================================
Strict validation proving that:
1. B+ never matches or overlaps with AB+
2. O+ never matches or overlaps with Bombay (Oh+)
3. Bombay (Oh-) and Rh-negative phenotypes are correctly isolated
"""


def normalize_blood_group(bg_raw: str) -> str:
    cleaned = bg_raw.strip().upper().replace(" ", "")
    # Check Bombay first before O+ or O-
    if "OH+" in cleaned or "OHPOS" in cleaned:
        return "Bombay (Oh+)"
    if "OH-" in cleaned or "OHNEG" in cleaned:
        return "Bombay (Oh-)"
    if "OH" in cleaned or "BOMBAY" in cleaned:
        return "Bombay (Oh+)"
    # Check AB before A or B
    if "AB+" in cleaned or "ABPOS" in cleaned or "AB+VE" in cleaned:
        return "AB+"
    if "AB-" in cleaned or "ABNEG" in cleaned or "AB-VE" in cleaned:
        return "AB-"
    # Check A
    if cleaned.startswith("A+") or "A+VE" in cleaned or cleaned == "A+":
        return "A+"
    if cleaned.startswith("A-") or "A-VE" in cleaned or cleaned == "A-":
        return "A-"
    # Check B
    if cleaned.startswith("B+") or "B+VE" in cleaned or cleaned == "B+":
        return "B+"
    if cleaned.startswith("B-") or "B-VE" in cleaned or cleaned == "B-":
        return "B-"
    # Check O
    if cleaned.startswith("O+") or "O+VE" in cleaned or cleaned == "O+":
        return "O+"
    if cleaned.startswith("O-") or "O-VE" in cleaned or cleaned == "O-":
        return "O-"
    return bg_raw.strip()


def test_b_plus_never_matches_ab_plus():
    b_variants = ["B+Ve", "B+", "B +ve", "B+VE", "b+ve"]
    ab_variants = ["AB+Ve", "AB+", "AB +ve", "AB+VE", "ab+ve"]

    for b in b_variants:
        norm = normalize_blood_group(b)
        assert norm == "B+", f"Expected B+ for {b}, got {norm}"
        assert norm != "AB+", f"Collision: {b} incorrectly normalized to AB+"

    for ab in ab_variants:
        norm = normalize_blood_group(ab)
        assert norm == "AB+", f"Expected AB+ for {ab}, got {norm}"
        assert norm != "B+", f"Collision: {ab} incorrectly normalized to B+"


def test_o_plus_never_matches_bombay_oh_plus():
    o_variants = ["O+Ve", "O+", "O +ve", "O+VE", "o+ve"]
    bombay_variants = ["Oh+VE", "Oh+", "Bombay", "Oh+ve", "Oh-VE"]

    for o in o_variants:
        norm = normalize_blood_group(o)
        assert norm == "O+", f"Expected O+ for {o}, got {norm}"
        assert "Bombay" not in norm, f"Collision: {o} incorrectly normalized to Bombay"

    for b in bombay_variants:
        norm = normalize_blood_group(b)
        assert "Bombay" in norm, f"Expected Bombay for {b}, got {norm}"
        assert norm != "O+", f"Collision: {b} incorrectly normalized to O+"


def test_rh_negative_phenotypes():
    assert normalize_blood_group("O-Ve") == "O-"
    assert normalize_blood_group("A-Ve") == "A-"
    assert normalize_blood_group("B-Ve") == "B-"
    assert normalize_blood_group("AB-Ve") == "AB-"
    assert normalize_blood_group("Oh-VE") == "Bombay (Oh-)"
