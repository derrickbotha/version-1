
import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class DisputeCreate(BaseModel):
    model_config = {"extra": "forbid"}

    contract_id: uuid.UUID
    reason: str = Field(..., min_length=20, max_length=2000)


class DisputeResolve(BaseModel):
    model_config = {"extra": "forbid"}

    resolution: str = Field(..., min_length=20)
    outcome: Literal["refund_student", "release_researcher", "split"]


class DisputeResponse(BaseModel):
    model_config = {"extra": "forbid", "from_attributes": True}

    id: uuid.UUID
    contract_id: uuid.UUID
    opened_by: uuid.UUID
    reason: str
    status: str
    resolution: Optional[str]
    created_at: datetime
