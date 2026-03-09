
import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SubmissionCreate(BaseModel):
    model_config = {"extra": "forbid"}

    contract_id: uuid.UUID
    submission_notes: str = Field(..., min_length=10, max_length=2000)


class RevisionRequest(BaseModel):
    model_config = {"extra": "forbid"}

    message: str = Field(..., min_length=10, max_length=1000)


class SubmissionResponse(BaseModel):
    model_config = {"extra": "forbid", "from_attributes": True}

    id: uuid.UUID
    contract_id: uuid.UUID
    researcher_id: uuid.UUID
    submission_notes: str | None
    status: str
    submitted_at: datetime  # mapped from created_at on the ORM model
    files: list[str]


class RevisionResponse(BaseModel):
    model_config = {"extra": "forbid", "from_attributes": True}

    id: uuid.UUID
    submission_id: uuid.UUID
    requested_by: uuid.UUID
    message: str | None
    created_at: datetime
