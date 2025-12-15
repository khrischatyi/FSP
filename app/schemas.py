from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, date
from typing import Optional, List
from app.models import ContractStatus, ConflictStatus


# Contract Schemas
class ContractCreate(BaseModel):
    """Schema for creating a new contract"""
    external_id: str = Field(..., description="Lender's own reference ID")
    address_street: str = Field(..., description="Street address")
    address_city: str = Field(..., description="City")
    address_state: str = Field(..., min_length=2, max_length=2, description="State (2-letter code)")
    address_zip: str = Field(..., description="ZIP code")
    apn: Optional[str] = Field(None, description="Assessor's Parcel Number")
    email: Optional[str] = Field(None, description="Contact email")
    phone: Optional[str] = Field(None, description="Contact phone")
    signed_date: date = Field(..., description="Date contract was signed (YYYY-MM-DD)")


class ContractUpdate(BaseModel):
    """Schema for updating contract status"""
    status: ContractStatus
    funded_date: Optional[date] = None
    cancelled_date: Optional[date] = None


class ConflictInfo(BaseModel):
    """Information about a conflicting contract"""
    lender: str = Field(..., description="Name of the other lender")
    signed_date: date = Field(..., description="When their contract was signed")
    match_reasons: List[str] = Field(..., description="Why contracts match (apn, address, email, phone)")
    days_since_signed: int = Field(..., description="Days since their contract was signed")

    class Config:
        from_attributes = True


class ContractResponse(BaseModel):
    """Response after contract submission"""
    status: str = Field(..., description="NO_HIT or EXISTING_CONTRACT")
    contract_id: str = Field(..., description="UUID of created contract")
    conflicts: Optional[List[ConflictInfo]] = Field(default=None, description="List of conflicting contracts")

    class Config:
        from_attributes = True


class ContractUpdateResponse(BaseModel):
    """Response after updating contract"""
    contract_id: str
    status: ContractStatus
    conflicts_resolved: int = Field(..., description="Number of conflicts resolved")

    class Config:
        from_attributes = True


# Webhook Schemas
class WebhookPayload(BaseModel):
    """Webhook event payload"""
    event: str
    timestamp: datetime
    data: dict


# Lender Schemas
class LenderCreate(BaseModel):
    """Schema for creating a lender"""
    name: str
    webhook_url: Optional[str] = None


class LenderResponse(BaseModel):
    """Lender information"""
    lender_id: str
    name: str
    api_key: str
    webhook_url: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Health Check
class HealthCheckResponse(BaseModel):
    status: str
    timestamp: datetime
    database: str
