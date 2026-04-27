"""
Supplier API schemas.
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SupplierBase(BaseModel):
    supplier_code: str = Field(..., min_length=2, max_length=100)
    legal_name: str = Field(..., min_length=2, max_length=255)
    business_type: str = Field(default="manufacturer", min_length=2, max_length=100)
    registration_number: Optional[str] = Field(default=None, max_length=255)
    country: str = Field(..., min_length=2, max_length=120)
    city: Optional[str] = Field(default=None, max_length=120)
    address: Optional[str] = Field(default=None, max_length=1000)
    contact_name: Optional[str] = Field(default=None, max_length=255)
    contact_email: Optional[str] = Field(default=None, max_length=255)
    contact_phone: Optional[str] = Field(default=None, max_length=100)
    status: str = Field(default="active", max_length=50)
    material_profiles: list[dict] = Field(default_factory=list)
    facilities: list[dict] = Field(default_factory=list)
    lane_preferences: list[dict] = Field(default_factory=list)
    notes: Optional[str] = Field(default=None, max_length=2000)


class SupplierCreate(SupplierBase):
    company_id: Optional[str] = Field(default=None, max_length=255)


class SupplierUpdate(BaseModel):
    legal_name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    business_type: Optional[str] = Field(default=None, min_length=2, max_length=100)
    registration_number: Optional[str] = Field(default=None, max_length=255)
    country: Optional[str] = Field(default=None, min_length=2, max_length=120)
    city: Optional[str] = Field(default=None, max_length=120)
    address: Optional[str] = Field(default=None, max_length=1000)
    contact_name: Optional[str] = Field(default=None, max_length=255)
    contact_email: Optional[str] = Field(default=None, max_length=255)
    contact_phone: Optional[str] = Field(default=None, max_length=100)
    status: Optional[str] = Field(default=None, max_length=50)
    material_profiles: Optional[list[dict]] = None
    facilities: Optional[list[dict]] = None
    lane_preferences: Optional[list[dict]] = None
    notes: Optional[str] = Field(default=None, max_length=2000)


class SupplierRead(SupplierBase):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    company_id: str
    created_at: datetime
    updated_at: datetime


class SupplierList(BaseModel):
    items: list[SupplierRead]
    total: int

