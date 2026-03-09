
import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class EscrowDepositRequest(BaseModel):
    model_config = {"extra": "forbid"}

    contract_id: uuid.UUID
    payment_provider: str
    provider_reference: str


class WalletDepositRequest(BaseModel):
    model_config = {"extra": "forbid"}

    amount: Decimal = Field(..., gt=0, decimal_places=2)


class PaymentReleaseRequest(BaseModel):
    model_config = {"extra": "forbid"}

    contract_id: uuid.UUID


class PaymentRefundRequest(BaseModel):
    model_config = {"extra": "forbid"}

    contract_id: uuid.UUID
    reason: str = Field(..., min_length=10)


class PaymentResponse(BaseModel):
    model_config = {"extra": "forbid", "from_attributes": True}

    id: uuid.UUID
    contract_id: uuid.UUID
    student_id: uuid.UUID
    researcher_id: uuid.UUID
    amount: Decimal
    status: str
    payment_provider: str | None
    created_at: datetime


class WalletResponse(BaseModel):
    model_config = {"extra": "forbid", "from_attributes": True}

    user_id: uuid.UUID
    balance: Decimal


class WalletTransactionResponse(BaseModel):
    model_config = {"extra": "forbid", "from_attributes": True}

    id: uuid.UUID
    amount: Decimal
    transaction_type: str
    created_at: datetime


class WalletTransactionListResponse(BaseModel):
    model_config = {"extra": "forbid"}

    items: list[WalletTransactionResponse]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Payment methods
# ---------------------------------------------------------------------------

class PaymentMethodResponse(BaseModel):
    model_config = {"extra": "forbid", "from_attributes": True}

    id: uuid.UUID
    provider: str
    brand: str | None
    last4: str | None
    expiry_month: int | None
    expiry_year: int | None
    is_default: bool
    created_at: datetime


class SetDefaultPaymentMethodRequest(BaseModel):
    model_config = {"extra": "forbid"}

    payment_method_id: uuid.UUID


# ---------------------------------------------------------------------------
# Writer payout
# ---------------------------------------------------------------------------

class PayoutRequestSchema(BaseModel):
    model_config = {"extra": "forbid"}

    amount: Decimal = Field(..., gt=0, decimal_places=2)
    provider: str = Field(..., pattern="^(stripe|paypal)$")

    @field_validator("amount")
    @classmethod
    def min_payout(cls, v: Decimal) -> Decimal:
        if v < Decimal("10.00"):
            raise ValueError("Minimum payout amount is $10.00")
        return v


class WriterPayoutResponse(BaseModel):
    model_config = {"extra": "forbid", "from_attributes": True}

    id: uuid.UUID
    writer_id: uuid.UUID
    amount: Decimal
    currency: str
    status: str
    provider: str | None
    created_at: datetime


class WriterPayoutListResponse(BaseModel):
    model_config = {"extra": "forbid"}

    items: list[WriterPayoutResponse]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Stripe — create PaymentIntent for wallet top-up
# ---------------------------------------------------------------------------

class StripeDepositRequest(BaseModel):
    model_config = {"extra": "forbid"}

    amount: Decimal = Field(..., gt=0, decimal_places=2)
    save_method: bool = False


class StripeDepositResponse(BaseModel):
    model_config = {"extra": "forbid"}

    client_secret: str
    payment_intent_id: str
    publishable_key: str


# ---------------------------------------------------------------------------
# Fraud event (internal)
# ---------------------------------------------------------------------------

class FraudFlagResponse(BaseModel):
    model_config = {"extra": "forbid"}

    flagged: bool
    reason: str | None = None
