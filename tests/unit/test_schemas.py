from datetime import datetime

from bloodlake.api.schemas import (
    BloodAvailabilityItem,
    BloodBankItem,
    MetaResponse,
)


def test_blood_bank_item_schema():
    item = BloodBankItem(
        hospital_code=1001,
        hospital_name="Apex Blood Center",
        hospital_type="Government",
        facility_type="Blood Bank",
        state_name="Gujarat",
        district_name="Anand",
        hospital_contact="02692-223344",
        hospital_address="Station Road, Anand",
        last_updated_at=datetime(2026, 10, 14, 12, 0, 0),
        reliability_score=92,
        reliability_tier="HIGH",
        latitude=22.5645,
        longitude=72.9289,
        is_approximate_location=True,
    )
    assert item.hospital_code == 1001
    assert item.reliability_tier == "HIGH"
    assert item.is_approximate_location is True


def test_blood_availability_item_schema():
    item = BloodAvailabilityItem(
        hospital_code=1001,
        hospital_name="Apex Blood Center",
        state_name="Gujarat",
        district_name="Anand",
        component_name="Packed Red Blood Cells",
        blood_group="O+",
        units=25,
        reliability_score=85,
        reliability_tier="HIGH",
    )
    assert item.units == 25
    assert item.blood_group == "O+"
    assert item.component_name == "Packed Red Blood Cells"


def test_meta_response_schema():
    meta = MetaResponse(
        project_name="eRaktKosh Blood Lakehouse",
        project_subtitle="National Blood Inventory Intelligence & Emergency Finder",
        version="1.0.0",
        institution="Academic Research Initiative",
        department="Faculty of Computer Science and Applications",
        academic_guide="Academic Mentor",
        author="Radhey Gajera",
        last_synced_at="2026-10-15 14:00:00",
        total_facilities=4692,
        data_source="eRaktKosh",
        attribution="Academic project",
        disclaimer="Call to confirm",
    )
    assert meta.total_facilities == 4692
    assert "Academic" in meta.institution
