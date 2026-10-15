from datetime import datetime

from bloodgrid.api.schemas.availability import (
    BloodBankSummary,
    ComponentStockItem,
    FacilityAvailabilityResponse,
)


def test_blood_bank_summary_schema():
    summary = BloodBankSummary(
        hospital_code=1001,
        hospital_name="Apex Blood Center",
        hospital_type="Government",
        facility_type="Blood Bank",
        state_name="Gujarat",
        district_name="Anand",
        hospital_contact="02692-223344",
        hospital_address="Station Road, Anand",
        source_updated_at=datetime(2026, 10, 14, 12, 0, 0),
        reliability_score=92,
        reliability_tier="HIGH",
        latitude=22.5645,
        longitude=72.9289,
        precision="exact",
    )
    assert summary.hospital_code == 1001
    assert summary.reliability_tier == "HIGH"
    assert summary.precision == "exact"


def test_component_stock_item_schema():
    item = ComponentStockItem(component_name="Packed Red Blood Cells", blood_group="O+", units=25)
    assert item.units == 25
    assert item.blood_group == "O+"


def test_facility_availability_response_schema():
    summary = BloodBankSummary(
        hospital_code=1001,
        hospital_name="Apex Blood Center",
        hospital_type="Government",
        facility_type="Blood Bank",
        state_name="Gujarat",
        district_name="Anand",
        hospital_contact="02692-223344",
        hospital_address="Station Road, Anand",
    )
    resp = FacilityAvailabilityResponse(
        facility=summary,
        matched_component="Packed Red Blood Cells",
        matched_blood_group="O+",
        available_units=15,
        all_components_stock={"Packed Red Blood Cells": {"O+": 15, "A+": 10}},
    )
    assert resp.available_units == 15
    assert "Not an official service" in resp.call_to_confirm_notice
