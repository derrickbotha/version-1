import uuid, enum
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum as SAEnum, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from ..database import Base

class AssignmentStatus(str, enum.Enum):
    pending      = "pending"
    researching  = "researching"
    writing      = "writing"
    qa_check     = "qa_check"
    prof_review  = "prof_review"
    completed    = "completed"
    failed       = "failed"

class DeliveryMethod(str, enum.Enum):
    download     = "download"
    lms_upload   = "lms_upload"
    email        = "email"

class ReviewType(str, enum.Enum):
    agent_only      = "agent_only"
    agent_professor = "agent_professor"

class Assignment(Base):
    __tablename__ = "assignments"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id          = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Assignment details (from student form)
    title            = Column(String(500), nullable=False)
    module_code      = Column(String(100))
    topic            = Column(Text)
    instructions     = Column(Text)
    focus_area       = Column(Text)         # e.g. "focus on insurance sector"
    word_count       = Column(Integer, default=2000)
    academic_level   = Column(String(50))
    deadline         = Column(DateTime)
    citation_style   = Column(String(20), default="Harvard")

    # LMS credentials (for auto-submit)
    lms_url          = Column(String(500))
    lms_username     = Column(String(255))
    lms_password_enc = Column(Text)         # encrypted at rest
    lms_assignment_id = Column(String(100))

    # Delivery preferences
    delivery_method  = Column(SAEnum(DeliveryMethod), default=DeliveryMethod.download)
    delivery_email   = Column(String(255))
    review_type      = Column(SAEnum(ReviewType), default=ReviewType.agent_only)

    # Execution state
    status           = Column(SAEnum(AssignmentStatus), default=AssignmentStatus.pending)
    n8n_execution_id = Column(String(255))
    pipeline_log     = Column(JSONB, default=list)

    # Output
    docx_path        = Column(Text)
    docx_s3_key      = Column(Text)
    plagiarism_score = Column(String(20))
    quality_score    = Column(Integer)

    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user         = relationship("User", back_populates="assignments")
    submission   = relationship("AssignmentSubmission", back_populates="assignment", uselist=False)
    delivery     = relationship("Delivery", back_populates="assignment", uselist=False)
    order        = relationship("Order", back_populates="assignment", uselist=False)

class AssignmentSubmission(Base):
    __tablename__ = "assignment_submissions"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey("assignments.id"), nullable=False)
    content_md    = Column(Text)
    content_docx  = Column(Text)   # S3 key
    word_count    = Column(Integer)
    sources_used  = Column(JSONB, default=list)
    professor_notes = Column(Text)
    revision_count  = Column(Integer, default=0)
    submitted_at    = Column(DateTime, default=datetime.utcnow)

    assignment = relationship("Assignment", back_populates="submission")

class Delivery(Base):
    __tablename__ = "deliveries"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey("assignments.id"), nullable=False)
    method        = Column(SAEnum(DeliveryMethod))
    destination   = Column(Text)    # email or LMS URL
    delivered_at  = Column(DateTime)
    success       = Column(Boolean, default=False)
    error_message = Column(Text)

    assignment = relationship("Assignment", back_populates="delivery")
