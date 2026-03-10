from pydantic import BaseModel, EmailStr
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from enum import Enum

class DeliveryMethodEnum(str, Enum):
    download    = "download"
    lms_upload  = "lms_upload"
    email       = "email"

class ReviewTypeEnum(str, Enum):
    agent_only      = "agent_only"
    agent_professor = "agent_professor"

class AssignmentCreate(BaseModel):
    title: str
    module_code: Optional[str] = None
    topic: str
    instructions: Optional[str] = None
    focus_area: Optional[str] = None      # e.g. "focus on insurance sector"
    word_count: int = 2000
    academic_level: str = "undergraduate"
    deadline: Optional[datetime] = None
    citation_style: str = "Harvard"

    # LMS credentials (only needed for lms_upload)
    lms_url: Optional[str] = None
    lms_username: Optional[str] = None
    lms_password: Optional[str] = None   # encrypted before storing
    lms_assignment_id: Optional[str] = None

    # Delivery
    delivery_method: DeliveryMethodEnum = DeliveryMethodEnum.download
    delivery_email: Optional[EmailStr] = None
    review_type: ReviewTypeEnum = ReviewTypeEnum.agent_only

class AssignmentOut(BaseModel):
    id: UUID
    title: str
    topic: str
    status: str
    review_type: str
    delivery_method: str
    word_count: int
    plagiarism_score: Optional[str]
    quality_score: Optional[int]
    docx_path: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class AssignmentStatusOut(BaseModel):
    id: UUID
    status: str
    pipeline_log: List[dict]
    n8n_execution_id: Optional[str]
    updated_at: datetime

    class Config:
        from_attributes = True
