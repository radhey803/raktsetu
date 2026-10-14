"""
BloodGrid Facility & Availability Schemas
=========================================
Pydantic v2 schemas for blood banks, stock items, and availability search results.
"""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class BloodBankSummary(BaseModel):
    hospital_code: int = Field(..., description="Unique facility identifier")
    hospital_name: str
    hospital_type: str
    facility_type: str
    state_name: str
    district_name: str
    hospital_contact: str
    hospital_address: str
    source_updated_at: Optional[datetime] = None
    days_since_update: Optional[int] = None
    reliability_score: int = Field(default=0, ge=0, le=100)
    reliability_tier: str = Field(default="UNKNOWN")
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    precision: str = Field(default="district_centroid")


class ComponentStockItem(BaseModel):
    component_name: str
    blood_group: str
    units: int = Field(..., ge=0)
    source_updated_at: Optional[datetime] = None


class FacilityAvailabilityResponse(BaseModel):
    facility: BloodBankSummary
    matched_component: str
    matched_blood_group: Optional[str] = None
    available_units: int = Field(..., ge=0)
    all_components_stock: Dict[str, Dict[str, int]] = Field(default_factory=dict)
    call_to_confirm_notice: str = Field(
        default="Data sourced from eRaktKosh. Not an official service. Always call the blood bank to confirm before travelling."
    )
