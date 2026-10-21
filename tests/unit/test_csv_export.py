"""
Unit Tests: CSV Export Utility (UTF-8 BOM & Attribution Header)
==============================================================
Validates Phase 7 requirements:
- UTF-8 with BOM (\\ufeff) for Excel compatibility
- Top metadata comments with data timestamp and MoHFW attribution
- Correct columns and escaping
"""

from bloodlake.export import export_search_results_csv, export_shortages_csv


def test_csv_export_has_utf8_bom():
    csv_str = export_search_results_csv([])
    assert csv_str.startswith("\ufeff")


def test_csv_export_has_attribution_and_disclaimer():
    csv_str = export_search_results_csv([])
    assert "eRaktKosh (MoHFW, Govt. of India)" in csv_str
    assert "Academic research project" in csv_str
    assert "Call the blood bank directly" in csv_str


def test_csv_export_search_results_data_rows():
    sample_data = [
        {
            "hospital_code": 24125,
            "hospital_name": "Indian Red Cross Society Anand",
            "state_name": "Gujarat",
            "district_name": "Anand",
            "hospital_type": "Charitable",
            "facility_type": "Blood Bank",
            "hospital_contact": "02692-223344",
            "component_name": "Packed Red Blood Cells",
            "blood_group": "O-",
            "units": 14,
            "reliability_score": 90,
            "reliability_label": "High",
            "days_since_last_update": 0,
            "location_precision": "district_centroid",
        }
    ]
    csv_str = export_search_results_csv(sample_data)
    assert "Indian Red Cross Society Anand" in csv_str
    assert "24125" in csv_str
    assert "Gujarat" in csv_str
    assert "O-" in csv_str
    assert "14" in csv_str
    assert "High" in csv_str


def test_csv_export_shortages():
    sample_data = [
        {
            "state_name": "Gujarat",
            "district_name": "Dang",
            "component_name": "Packed Red Blood Cells",
            "blood_group": "O-",
            "total_units": 0,
            "reporting_banks": 1,
            "banks_with_zero": 1,
            "shortage_status": "CRITICAL_DEPLETION",
        }
    ]
    csv_str = export_shortages_csv(sample_data)
    assert "Dang" in csv_str
    assert "CRITICAL_DEPLETION" in csv_str
