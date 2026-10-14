"""
BloodGrid System Meta & Authentication Schemas
==============================================
Pydantic v2 schemas for health checks, data synchronization metadata,
user authentication, and API key management.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class SystemMetaResponse(BaseModel):
    version: str
    environment: str
    last_sync_timestamp: Optional[datetime] = None
    last_sync_status: str
    total_reporting_facilities: int
    total_inventory_records: int
    data_freshness_status: str  # CURRENT / STALE
    is_stale_warning: bool  # True if last sync > 12 hours ago
    source_attribution: str


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2)
    organization_name: Optional[str] = None


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in_minutes: int


class ApiKeyCreateRequest(BaseModel):
    key_name: str = Field(..., min_length=3, max_length=50)
    tier: str = Field(default="pro", description="pro, developer, or organization")


class ApiKeyCreatedResponse(BaseModel):
    key_id: str
    key_name: str
    api_key_secret: str = Field(
        ..., description="Secret key shown ONCE upon creation. Store safely."
    )
    tier: str
    rate_limit: str
    created_at: datetime
