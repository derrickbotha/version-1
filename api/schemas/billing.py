from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class OrderCreate(BaseModel):
    assignment_id: Optional[UUID] = None
    review_type: str = "agent_only"
    payment_method: str = "stripe"   # stripe or paypal

class OrderOut(BaseModel):
    id: UUID
    amount: float
    currency: str
    status: str
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class CheckoutSession(BaseModel):
    checkout_url: str
    order_id: UUID
    amount: float

class SubscriptionOut(BaseModel):
    id: UUID
    plan: str
    status: str
    current_period_end: Optional[datetime]
    cancel_at_period_end: bool

    class Config:
        from_attributes = True
