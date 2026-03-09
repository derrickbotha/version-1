
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class ProfileUpdateRequest(BaseModel):
    model_config = {"extra": "forbid"}

    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)
    phone: str | None = Field(None, max_length=30)
    whatsapp_number: str | None = Field(None, max_length=30)


class ContactUpdateRequest(BaseModel):
    model_config = {"extra": "forbid"}

    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=30)
    whatsapp_number: str | None = Field(None, max_length=30)


class LocationUpdateRequest(BaseModel):
    model_config = {"extra": "forbid"}

    country: str | None = Field(None, max_length=100)
    city: str | None = Field(None, max_length=100)
    postal_code: str | None = Field(None, max_length=20)
    timezone: str | None = Field(None, max_length=50)


class PasswordChangeRequest(BaseModel):
    model_config = {"extra": "forbid"}

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)


class ProfileResponse(BaseModel):
    model_config = {"extra": "forbid", "from_attributes": True}

    id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    role: str
    phone: str | None
    whatsapp_number: str | None
    is_verified: bool
    status: str
    created_at: datetime


class StudentProfileResponse(BaseModel):
    model_config = {"extra": "forbid", "from_attributes": True}

    university: str | None
    degree_program: str | None
    country: str | None


class ResearcherProfileResponse(BaseModel):
    model_config = {"extra": "forbid", "from_attributes": True}

    bio: str | None
    expertise: list[str] | None
    rating: float
    total_jobs_completed: int


class AccountResponse(BaseModel):
    model_config = {"extra": "forbid"}

    profile: ProfileResponse
    student_profile: StudentProfileResponse | None = None
    researcher_profile: ResearcherProfileResponse | None = None


class StudentProfileUpdateRequest(BaseModel):
    model_config = {"extra": "forbid"}

    university: str | None = Field(None, max_length=255)
    degree_program: str | None = Field(None, max_length=255)
    country: str | None = Field(None, max_length=100)


class ResearcherProfileUpdateRequest(BaseModel):
    model_config = {"extra": "forbid"}

    bio: str | None = Field(None, max_length=2000)
    expertise: list[str] | None = None
