"""
Pydantic API Request & Response Schemas
======================================
Defines strongly-typed contracts for all Lakehouse analytical queries,
filters, pagination, and metadata responses.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class BloodBankItem(BaseModel):
    hospital_code: int
    hospital_name: str
    hospital_type: Optional[str] = None
    facility_type: Optional[str] = None
    state_name: str
    district_name: str
    hospital_contact: Optional[str] = None
    hospital_address: Optional[str] = None
    last_updated_at: Optional[datetime] = None
    days_since_last_update: Optional[int] = None
    data_freshness_status: Optional[str] = "UNKNOWN"
    stock_alert_level: Optional[str] = "NORMAL"
    reliability_score: int = 50
    reliability_label: str = "Medium"
    reliability_tier: str = "Medium"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_approximate_location: bool = True
    location_precision: str = "district_centroid"
    distance_km: Optional[float] = None
    available_stock_summary: Optional[Dict[str, int]] = None


class BloodAvailabilityItem(BaseModel):
    hospital_code: int
    hospital_name: str
    hospital_type: Optional[str] = None
    facility_type: Optional[str] = None
    state_name: str
    district_name: str
    hospital_contact: Optional[str] = None
    hospital_address: Optional[str] = None
    component_name: str
    blood_group: str
    units: int
    last_updated_at: Optional[datetime] = None
    days_since_last_update: Optional[int] = None
    reliability_score: int = 50
    reliability_label: str = "Medium"
    reliability_tier: str = "Medium"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_approximate_location: bool = True
    location_precision: str = "district_centroid"
    distance_km: Optional[float] = None


class EmergencyFacilityItem(BaseModel):
    hospital_code: int
    hospital_name: str
    hospital_type: Optional[str] = None
    facility_type: Optional[str] = None
    state_name: str
    district_name: str
    hospital_contact: Optional[str] = None
    hospital_address: Optional[str] = None
    latitude: float
    longitude: float
    is_approximate_location: bool = True
    location_precision: str = "district_centroid"
    distance_km: Optional[float] = None
    reliability_score: int = 50
    reliability_label: str = "Medium"
    days_since_last_update: Optional[int] = None
    last_updated_at: Optional[datetime] = None
    total_compatible_units: int
    units_by_group: Dict[str, int]
    rank_score: float
    why_ranked_here: str


class EmergencyResponse(BaseModel):
    patient_blood_group: str
    component_name: str
    compatible_donor_groups: List[str]
    is_rh_negative: bool
    is_rare_phenotype: bool
    clinical_warning: Optional[str] = None
    source_attribution: str
    disclaimer: str
    total_found: int
    top_facilities: List[EmergencyFacilityItem]


class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int


class StateSummaryItem(BaseModel):
    state: str
    banks: int


class NationalSummary(BaseModel):
    total_banks: int
    total_states: int
    fresh_banks_24h: int
    stale_banks_30d: int
    top_states: List[StateSummaryItem]


class DistrictShortage(BaseModel):
    state_name: str
    district_name: str
    blood_group: str
    component_name: str
    total_units: int
    reporting_banks: int
    banks_with_zero: int = 0
    shortage_status: str
    severity_score: int = 0


class RareBloodItem(BaseModel):
    hospital_code: int
    hospital_name: str
    state_name: str
    district_name: str
    blood_group: str
    component_name: str
    units: int
    hospital_contact: Optional[str] = None
    last_updated_at: Optional[datetime] = None
    days_since_last_update: Optional[int] = None
    reliability_score: int = 50
    reliability_label: str = "Medium"


class TrendPoint(BaseModel):
    snapshot_date: str
    units: int


class TrendResponse(BaseModel):
    hospital_code: int
    hospital_name: Optional[str] = None
    component_name: str
    blood_group: str
    points: List[TrendPoint]
    has_sufficient_history: bool
    message: str


class MetaResponse(BaseModel):
    project_name: str
    project_subtitle: str
    version: str
    institution: str
    department: str
    academic_guide: str
    author: str
    last_synced_at: Optional[str] = None
    total_facilities: int
    data_source: str
    attribution: str
    disclaimer: str
