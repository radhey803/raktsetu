"""
BloodGrid Ingestion Data Models
===============================
Pydantic models representing eRaktKosh district payloads and pipeline metadata.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class FacilityRawRecord(BaseModel):
    hospital_code: Optional[int] = Field(default=None, alias="hospitalCode")
    hospital_name: Optional[str] = Field(default=None, alias="hospitalname")
    hospital_address: Optional[str] = Field(default=None, alias="hospitaladd")
    hospital_contact: Optional[str] = Field(default=None, alias="hospitalcontact")
    hospital_type: Optional[str] = Field(default=None, alias="hospitalType")
    facility_type: Optional[str] = Field(default=None, alias="type")
    state_code: Optional[str] = Field(default=None, alias="stateCode")
    district_code: Optional[str] = Field(default=None, alias="districtCode")
    state_name: Optional[str] = Field(default=None, alias="State")
    district_name: Optional[str] = Field(default=None, alias="District")
    entry_date: Optional[str] = Field(default=None, alias="entrydate")
    components_raw: Optional[Any] = Field(default=None, alias="components")
    available_with_qty: Optional[str] = Field(default=None, alias="available_WithQty")
    not_available_with_qty: Optional[str] = Field(default=None, alias="not_available_WithQty")
    moderate_stock: Optional[int] = Field(default=None, alias="moderateStock")


class ScrapeRunMetadata(BaseModel):
    run_id: str
    scraped_at: datetime
    source_url: str
    districts_attempted: int
    districts_successful: int
    districts_failed: int
    error_rate_pct: float
    total_facilities_extracted: int
    file_path: str
    file_sha256: str
    duration_seconds: float
