"""
Unit Tests: CSV Export Utility (UTF-8 BOM & Attribution Header)
==============================================================
Validates Phase 7 requirements:
- UTF-8 with BOM (\\ufeff) for Excel compatibility
- Header on the first row and a Source column with MoHFW attribution
- Correct columns and escaping
"""

from bloodlake.export import export_search_results_csv, export_shortages_csv


def test_csv_export_has_utf8_bom():
    csv_str = export_search_results_csv([])
    assert csv_str.startswith("\ufeff")


def test_csv_export_header_first_with_source_column():
    csv_str = export_search_results_csv(
        [{"hospital_name": "=cmd", "hospital_contact": "Phone: 123 ,Fax: 9, Email: a@b.in"}]
    )
    header, row = csv_str.lstrip("\ufeff").splitlines()[:2]
    assert header.startswith("Hospital Code,") and header.endswith(",Source")
    assert "eRaktKosh (MoHFW, Govt. of India)" in row
    assert "'=cmd" in row and ",123,a@b.in," in row  # formula neutralised, contact split


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
    assert "Critical depletion" in csv_str
