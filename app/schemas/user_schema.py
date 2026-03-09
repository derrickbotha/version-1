
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRegister(BaseModel):
    model_config = {"extra": "forbid"}

    email: EmailStr
    password: str = Field(min_length=10, description="Minimum 10 characters")
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    role: str = Field(default="student", pattern="^(student|researcher)$")
    phone: str | None = Field(default=None, max_length=30)

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


class UserLogin(BaseModel):
    model_config = {"extra": "forbid"}

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    model_config = {"extra": "forbid"}

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    model_config = {"extra": "forbid", "from_attributes": True}

    id: uuid.UUID
    email: EmailStr
    first_name: str
    last_name: str
    role: str
    is_verified: bool
    created_at: datetime


class UserUpdate(BaseModel):
    model_config = {"extra": "forbid"}

    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=30)

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        if v is not None:
            return v.strip()
        return v


class RefreshTokenRequest(BaseModel):
    model_config = {"extra": "forbid"}

    refresh_token: str
