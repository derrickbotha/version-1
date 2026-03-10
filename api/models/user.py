import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Numeric, ForeignKey, Text, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from ..database import Base

class AcademicLevel(str, enum.Enum):
    high_school  = "high_school"
    undergraduate = "undergraduate"
    postgraduate = "postgraduate"
    phd          = "phd"

class User(Base):
    __tablename__ = "users"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email         = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name     = Column(String(255), nullable=False)
    academic_level = Column(SAEnum(AcademicLevel), default=AcademicLevel.undergraduate)
    institution   = Column(String(255))
    is_active     = Column(Boolean, default=True)
    is_verified   = Column(Boolean, default=False)
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    wallet        = relationship("Wallet", back_populates="user", uselist=False)
    subscription  = relationship("Subscription", back_populates="user", uselist=False)
    assignments   = relationship("Assignment", back_populates="user")

class Wallet(Base):
    __tablename__ = "wallets"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    balance    = Column(Numeric(12, 2), default=0)
    currency   = Column(String(3), default="USD")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user         = relationship("User", back_populates="wallet")
    transactions = relationship("WalletTransaction", back_populates="wallet")

class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wallet_id   = Column(UUID(as_uuid=True), ForeignKey("wallets.id"), nullable=False)
    amount      = Column(Numeric(12, 2), nullable=False)
    tx_type     = Column(String(50))   # deposit, debit, refund
    description = Column(Text)
    reference   = Column(String(255))
    created_at  = Column(DateTime, default=datetime.utcnow)

    wallet = relationship("Wallet", back_populates="transactions")
