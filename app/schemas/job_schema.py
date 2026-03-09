
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated, Optional

from pydantic import BaseModel, Field, field_validator


class JobCreate(BaseModel):
    model_config = {"extra": "forbid"}

    title: str = Field(min_length=5, max_length=255)
    description: str = Field(min_length=20)
    subject: str = Field(min_length=1, max_length=150)
    academic_level: str = Field(min_length=1, max_length=100)
    proposed_price: Decimal = Field(gt=Decimal("0"), decimal_places=2)
    deadline: datetime

    @field_validator("deadline")
    @classmethod
    def deadline_must_be_future(cls, v: datetime) -> datetime:
        now = datetime.now(timezone.utc)
        # Make deadline timezone-aware if naive
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        if v <= now:
            raise ValueError("deadline must be a future datetime")
        return v

    @field_validator("title", "description", "subject", "academic_level", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip()
        return v


class JobUpdate(BaseModel):
    model_config = {"extra": "forbid"}

    title: Optional[str] = Field(default=None, min_length=5, max_length=255)
    description: Optional[str] = Field(default=None, min_length=20)
    subject: Optional[str] = Field(default=None, min_length=1, max_length=150)
    academic_level: Optional[str] = Field(default=None, min_length=1, max_length=100)
    proposed_price: Optional[Annotated[Decimal, Field(gt=Decimal("0"), decimal_places=2)]] = None
    deadline: Optional[datetime] = None

    @field_validator("deadline")
    @classmethod
    def deadline_must_be_future(cls, v: datetime | None) -> datetime | None:
        if v is None:
            return v
        now = datetime.now(timezone.utc)
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        if v <= now:
            raise ValueError("deadline must be a future datetime")
        return v

    @field_validator("title", "description", "subject", "academic_level", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        if isinstance(v, str):
            return v.strip()
        return v


class JobResponse(BaseModel):
    model_config = {"extra": "forbid", "from_attributes": True}

    id: uuid.UUID
    title: str
    description: str
    subject: str
    academic_level: str
    proposed_price: Decimal
    status: str
    deadline: Optional[datetime]
    student_id: uuid.UUID
    created_at: datetime


class JobListResponse(BaseModel):
    model_config = {"extra": "forbid"}

    items: list[JobResponse]
    total: int
    page: int
    page_size: int


class JobFilterParams(BaseModel):
    model_config = {"extra": "forbid"}

    status: Optional[str] = None
    subject: Optional[str] = None
    min_price: Optional[Decimal] = Field(default=None, gt=Decimal("0"))
    max_price: Optional[Decimal] = Field(default=None, gt=Decimal("0"))
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
