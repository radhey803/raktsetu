"""
BloodGrid API Common Schemas
============================
Pydantic v2 data models for standard API responses, pagination, and error envelopes.
"""

from typing import Any, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str = Field(..., description="Machine-readable error classification code")
    message: str = Field(..., description="Human-readable description of the error")
    details: Optional[Any] = Field(default=None, description="Optional granular field-level diagnostics")


class ErrorResponse(BaseModel):
    success: bool = Field(default=False)
    error: ErrorDetail
    request_id: str = Field(..., description="Unique request tracing ID")


class PaginationMeta(BaseModel):
    total: int = Field(..., description="Total matching items across all pages")
    limit: int = Field(..., description="Page size limit applied")
    offset: int = Field(..., description="Offset starting point")
    has_more: bool = Field(..., description="True if subsequent pages exist")


class PaginatedResponse(BaseModel, Generic[T]):
    success: bool = Field(default=True)
    data: List[T]
    pagination: PaginationMeta
    request_id: str
