
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class MessageCreate(BaseModel):
    model_config = {"extra": "forbid"}

    conversation_id: uuid.UUID
    content: str = Field(..., min_length=1, max_length=5000)
    channel: Literal["platform"] = "platform"


class MessageResponse(BaseModel):
    model_config = {"extra": "forbid", "from_attributes": True}

    id: uuid.UUID
    conversation_id: uuid.UUID
    sender_id: uuid.UUID | None
    message_type: str
    content: str
    file_url: str | None
    channel: str
    created_at: datetime


class ConversationResponse(BaseModel):
    model_config = {"extra": "forbid", "from_attributes": True}

    id: uuid.UUID
    job_id: uuid.UUID
    student_id: uuid.UUID
    researcher_id: uuid.UUID
    created_at: datetime


class ConversationListResponse(BaseModel):
    model_config = {"extra": "forbid"}

    items: list[ConversationResponse]


class MessageListResponse(BaseModel):
    model_config = {"extra": "forbid"}

    items: list[MessageResponse]
    total: int
    page: int
    page_size: int
