
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class RatingCreate(BaseModel):
    model_config = {"extra": "forbid"}

    contract_id: uuid.UUID
    rating: int = Field(..., ge=1, le=5)
    review: Optional[str] = Field(None, min_length=10, max_length=500)


class RatingResponse(BaseModel):
    model_config = {"extra": "forbid", "from_attributes": True}

    id: uuid.UUID
    contract_id: uuid.UUID
    student_id: uuid.UUID
    researcher_id: uuid.UUID
    rating: int
    review: Optional[str]
    created_at: datetime
