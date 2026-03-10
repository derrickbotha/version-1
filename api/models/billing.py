import uuid, enum
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Numeric, ForeignKey, Enum as SAEnum, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from ..database import Base

class PlanEnum(str, enum.Enum):
    starter      = "starter"
    professional = "professional"
    agentic_pro  = "agentic_pro"
    enterprise   = "enterprise"

class ReviewTypeEnum(str, enum.Enum):
    agent_only      = "agent_only"
    agent_professor = "agent_professor"

class OrderStatus(str, enum.Enum):
    pending   = "pending"
    paid      = "paid"
    refunded  = "refunded"
    failed    = "failed"

class Subscription(Base):
    __tablename__ = "subscriptions"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id         = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    plan            = Column(SAEnum(PlanEnum), default=PlanEnum.starter)
    stripe_sub_id   = Column(String(255))
    paypal_sub_id   = Column(String(255))
    status          = Column(String(50), default="active")   # active, cancelled, past_due
    current_period_start = Column(DateTime)
    current_period_end   = Column(DateTime)
    cancel_at_period_end = Column(Boolean, default=False)
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="subscription")

class Order(Base):
    __tablename__ = "orders"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id         = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    assignment_id   = Column(UUID(as_uuid=True), ForeignKey("assignments.id"), nullable=True)
    amount          = Column(Numeric(10, 2), nullable=False)
    currency        = Column(String(3), default="USD")
    description     = Column(Text)
    review_type     = Column(SAEnum(ReviewTypeEnum), default=ReviewTypeEnum.agent_only)
    professor_fee   = Column(Numeric(10, 2), default=0)
    status          = Column(SAEnum(OrderStatus), default=OrderStatus.pending)
    stripe_pi_id    = Column(String(255))
    paypal_order_id = Column(String(255))
    paid_at         = Column(DateTime)
    created_at      = Column(DateTime, default=datetime.utcnow)

    assignment = relationship("Assignment", back_populates="order")
