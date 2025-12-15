from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Integer, Text, Boolean, Date, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, date
import enum
import uuid
from app.database import Base


class ContractStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    FUNDED = "FUNDED"
    CANCELLED = "CANCELLED"


class ConflictStatus(str, enum.Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"


class WebhookEventType(str, enum.Enum):
    NEW_CONFLICT = "NEW_CONFLICT"
    CONFLICT_RESOLVED = "CONFLICT_RESOLVED"
    CONFLICT_CONTRACT_FUNDED = "CONFLICT_CONTRACT_FUNDED"


class Lender(Base):
    """Lender/Finance Provider"""
    __tablename__ = "lsp_lenders"

    id = Column(Integer, primary_key=True, index=True)
    lender_id = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()), nullable=False)
    name = Column(String(255), nullable=False)
    api_key = Column(String(255), unique=True, index=True, nullable=False)
    webhook_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    contracts = relationship("Contract", back_populates="lender")


class Contract(Base):
    """Contract submission from a lender"""
    __tablename__ = "lsp_contracts"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()), nullable=False)
    lender_id = Column(Integer, ForeignKey("lsp_lenders.id"), nullable=False, index=True)
    external_id = Column(String(255), nullable=False, index=True)  # Lender's own reference

    # Address fields (normalized)
    address_street = Column(String(500), nullable=False, index=True)
    address_city = Column(String(100), nullable=False)
    address_state = Column(String(2), nullable=False)
    address_zip = Column(String(10), nullable=False, index=True)
    apn = Column(String(100), nullable=True, index=True)  # Assessor's Parcel Number

    # Contact (normalized)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(20), nullable=True, index=True)

    # Dates
    signed_date = Column(Date, nullable=False, index=True)
    funded_date = Column(Date, nullable=True)
    cancelled_date = Column(Date, nullable=True)

    # Status
    status = Column(Enum(ContractStatus), default=ContractStatus.ACTIVE, nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    lender = relationship("Lender", back_populates="contracts")
    conflicts_as_a = relationship("Conflict", foreign_keys="Conflict.contract_a_id", back_populates="contract_a")
    conflicts_as_b = relationship("Conflict", foreign_keys="Conflict.contract_b_id", back_populates="contract_b")


class Conflict(Base):
    """Conflict between two contracts from different lenders"""
    __tablename__ = "lsp_conflicts"

    id = Column(Integer, primary_key=True, index=True)
    conflict_id = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()), nullable=False)

    # The two contracts in conflict
    contract_a_id = Column(Integer, ForeignKey("lsp_contracts.id"), nullable=False, index=True)
    contract_b_id = Column(Integer, ForeignKey("lsp_contracts.id"), nullable=False, index=True)

    # Match information
    match_reasons = Column(JSON, nullable=False)  # ["apn", "address", "email", "phone"]

    # Status
    status = Column(Enum(ConflictStatus), default=ConflictStatus.OPEN, nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)

    # Relationships
    contract_a = relationship("Contract", foreign_keys=[contract_a_id], back_populates="conflicts_as_a")
    contract_b = relationship("Contract", foreign_keys=[contract_b_id], back_populates="conflicts_as_b")


class WebhookLog(Base):
    """Log of webhook deliveries"""
    __tablename__ = "lsp_webhook_log"

    id = Column(Integer, primary_key=True, index=True)
    log_id = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()), nullable=False)
    lender_id = Column(Integer, ForeignKey("lsp_lenders.id"), nullable=False, index=True)
    event_type = Column(Enum(WebhookEventType), nullable=False)
    payload = Column(JSON, nullable=False)
    response_code = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    attempt = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    lender = relationship("Lender")
