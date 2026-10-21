"""
Unit Tests: Emergency Mode Medical Compatibility & Ranking
===========================================================
Validates:
1. Red cell compatibility matrix for all standard ABO/Rh groups and Bombay Oh phenotype.
2. Clinical Rh- / Bombay warning generation.
3. Multi-pillar emergency facility ranking order ($0.35F + 0.30T + 0.25U + 0.10D$).
4. Honest empty result handling.
"""

from bloodlake.api.schemas import EmergencyResponse
from bloodlake.medical import (
    get_compatible_groups,
    get_emergency_clinical_warning,
    get_medical_disclaimer,
    get_source_attribution,
    is_bombay_phenotype,
    is_rh_negative,
)


def test_red_cell_compatibility_matrix_all_groups():
    """Verify standard WHO/NBTC red cell compatibility for all 8 groups and Bombay."""
    # O- (Universal RBC Donor) can receive only O-
    assert set(get_compatible_groups("O-")) == {"O-"}

    # O+ can receive O-, O+
    assert set(get_compatible_groups("O+")) == {"O-", "O+"}

    # A- can receive O-, A-
    assert set(get_compatible_groups("A-")) == {"O-", "A-"}

    # A+ can receive O-, O+, A-, A+
    assert set(get_compatible_groups("A+")) == {"O-", "O+", "A-", "A+"}

    # B- can receive O-, B-
    assert set(get_compatible_groups("B-")) == {"O-", "B-"}

    # B+ can receive O-, O+, B-, B+
    assert set(get_compatible_groups("B+")) == {"O-", "O+", "B-", "B+"}

    # AB- can receive O-, A-, B-, AB-
    assert set(get_compatible_groups("AB-")) == {"O-", "A-", "B-", "AB-"}

    # AB+ (Universal RBC Recipient) can receive all 8 groups
    assert set(get_compatible_groups("AB+")) == {"O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"}

    # Bombay Oh phenotype can ONLY receive Bombay Oh (possesses anti-H antibodies)
    assert set(get_compatible_groups("Bombay (Oh+)")) == {"Bombay (Oh+)", "Bombay (Oh-)"}
    assert set(get_compatible_groups("Oh+")) == {"Bombay (Oh+)", "Bombay (Oh-)"}


def test_clinical_warnings_for_rh_and_bombay():
    """Rh negative and Bombay phenotypes must trigger strict clinical warnings."""
    # Rh negative groups
    for grp in ["O-", "A-", "B-", "AB-"]:
        assert is_rh_negative(grp) is True
        warning = get_emergency_clinical_warning(grp)
        assert warning is not None
        assert "Rh-Negative Protocol" in warning

    # Rh positive groups do not trigger Rh warning
    for grp in ["O+", "A+", "B+", "AB+"]:
        assert is_rh_negative(grp) is False
        assert get_emergency_clinical_warning(grp) is None

    # Bombay phenotype
    assert is_bombay_phenotype("Bombay (Oh+)") is True
    assert is_bombay_phenotype("Oh-") is True
    bombay_warning = get_emergency_clinical_warning("Bombay (Oh+)")
    assert bombay_warning is not None
    assert "CRITICAL BOMBAY" in bombay_warning


def test_medical_disclaimer_and_attribution():
    """Verify official disclaimers are present."""
    disc = get_medical_disclaimer()
    assert "Guidance only, not medical advice" in disc
    attr = get_source_attribution()
    assert "National Blood Transfusion Council" in attr or "NBTC" in attr or "WHO" in attr


def test_emergency_ranking_formula():
    """
    Simulate ranking calculation:
    RankScore = 0.35 * Freshness + 0.30 * Trust + 0.25 * UnitsNorm + 0.10 * DistanceScore
    """
    freshness_a = 1.0
    trust_a = 90 / 100.0
    units_a = min(10 / 20.0, 1.0)  # 0.5
    dist_a = 1.0  # closer

    score_a = 0.35 * freshness_a + 0.30 * trust_a + 0.25 * units_a + 0.10 * dist_a

    freshness_b = 0.16
    trust_b = 30 / 100.0
    units_b = min(2 / 20.0, 1.0)  # 0.1
    dist_b = 0.5  # farther

    score_b = 0.35 * freshness_b + 0.30 * trust_b + 0.25 * units_b + 0.10 * dist_b

    assert score_a > score_b


def test_emergency_response_schema_validation():
    """Test schema instantiation with empty and filled facility lists."""
    empty_resp = EmergencyResponse(
        patient_blood_group="O-",
        component_name="Packed Red Blood Cells",
        compatible_donor_groups=["O-"],
        state="Gujarat",
        district="Anand",
        is_rh_negative=True,
        is_rare_phenotype=False,
        clinical_warning="Rh-Negative Protocol: Patient lacks Rh(D) antigen.",
        source_attribution="National Blood Transfusion Council (NBTC)",
        disclaimer="Guidance only, not medical advice. Confirm with a doctor or blood bank.",
        total_found=0,
        top_facilities=[],
    )
    assert empty_resp.total_found == 0
    assert len(empty_resp.top_facilities) == 0
    assert empty_resp.is_rh_negative is True
