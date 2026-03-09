
import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class BidCreate(BaseModel):
    model_config = {"extra": "forbid"}

    proposed_price: Decimal = Field(gt=Decimal("0"), decimal_places=2)
    message: str = Field(min_length=10)

    @field_validator("message", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip()
        return v


class BidCounterOffer(BaseModel):
    model_config = {"extra": "forbid"}

    new_price: Decimal = Field(gt=Decimal("0"), decimal_places=2)
    message: str = Field(min_length=10)

    @field_validator("message", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip()
        return v


class BidResponse(BaseModel):
    model_config = {"extra": "forbid", "from_attributes": True}

    id: uuid.UUID
    job_id: uuid.UUID
    researcher_id: uuid.UUID
    proposed_price: Decimal
    message: str | None
    status: str
    created_at: datetime


class BidCounterResponse(BaseModel):
    model_config = {"extra": "forbid", "from_attributes": True}

    id: uuid.UUID
    bid_id: uuid.UUID
    counter_by: uuid.UUID
    new_price: Decimal
    message: str | None
    created_at: datetime


class BidListResponse(BaseModel):
    model_config = {"extra": "forbid"}

    items: list[BidResponse]
    total: int
