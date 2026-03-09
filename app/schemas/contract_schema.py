
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class ContractResponse(BaseModel):
    model_config = {"extra": "forbid", "from_attributes": True}

    id: uuid.UUID
    job_id: uuid.UUID
    student_id: uuid.UUID
    researcher_id: uuid.UUID
    agreed_price: Decimal
    start_date: Optional[datetime]
    deadline: Optional[datetime]
    status: str
    created_at: datetime


class ContractListResponse(BaseModel):
    model_config = {"extra": "forbid"}

    items: list[ContractResponse]
    total: int
