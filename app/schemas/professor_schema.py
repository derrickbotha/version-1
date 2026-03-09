"""Pydantic schemas for professor, institution, and academic review endpoints."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


# ─────────────────────────────────────────────────────────────────────────────
# Institution
# ─────────────────────────────────────────────────────────────────────────────

class InstitutionCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    country: Optional[str] = Field(None, max_length=100)
    domain: Optional[str] = Field(None, max_length=100, description="e.g. mit.edu")


class InstitutionResponse(BaseModel):
    id: uuid.UUID
    name: str
    country: Optional[str]
    domain: Optional[str]
    is_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Professor Profile
# ─────────────────────────────────────────────────────────────────────────────

class ProfessorProfileCreate(BaseModel):
    title: Optional[str] = Field(None, max_length=50)
    department: Optional[str] = Field(None, max_length=200)
    academic_rank: Optional[str] = Field(
        None,
        description=(
            "lecturer | assistant_professor | associate_professor | "
            "full_professor | emeritus | adjunct"
        ),
    )
    bio: Optional[str] = None
    expertise_areas: Optional[list[str]] = Field(default_factory=list)
    orcid_id: Optional[str] = Field(None, max_length=20)
    linkedin_url: Optional[str] = Field(None, max_length=500)
    institutional_email: Optional[str] = Field(None, max_length=255)
    institution_id: Optional[uuid.UUID] = None
    review_subjects: Optional[list[str]] = Field(default_factory=list)


class ProfessorProfileUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=50)
    department: Optional[str] = Field(None, max_length=200)
    academic_rank: Optional[str] = None
    bio: Optional[str] = None
    expertise_areas: Optional[list[str]] = None
    orcid_id: Optional[str] = None
    linkedin_url: Optional[str] = None
    institutional_email: Optional[str] = None
    review_subjects: Optional[list[str]] = None


class ProfessorProfileResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: Optional[str]
    department: Optional[str]
    academic_rank: Optional[str]
    bio: Optional[str]
    expertise_areas: Optional[list[str]]
    orcid_id: Optional[str]
    linkedin_url: Optional[str]
    institutional_email: Optional[str]
    institution: Optional[InstitutionResponse]
    status: str
    review_subjects: Optional[list[str]]
    total_reviews_completed: int
    avg_review_score_given: float
    review_fee_per_job: float
    approved_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Researcher Credential
# ─────────────────────────────────────────────────────────────────────────────

class CredentialSubmit(BaseModel):
    credential_type: str = Field(
        ...,
        description=(
            "bachelors_degree | masters_degree | phd | postdoc | "
            "professional_certification | publication | award | other"
        ),
    )
    institution_name: str = Field(..., max_length=255)
    field_of_study: Optional[str] = Field(None, max_length=255)
    year_obtained: Optional[int] = Field(None, ge=1900, le=2100)
    document_url: Optional[str] = Field(None, max_length=1000)
    notes: Optional[str] = None


class CredentialVerifyAction(BaseModel):
    action: str = Field(..., description="'verify' or 'reject'")
    rejection_reason: Optional[str] = None


class CredentialResponse(BaseModel):
    id: uuid.UUID
    researcher_id: uuid.UUID
    credential_type: str
    institution_name: str
    field_of_study: Optional[str]
    year_obtained: Optional[int]
    status: str
    verified_at: Optional[datetime]
    rejection_reason: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Endorsement
# ─────────────────────────────────────────────────────────────────────────────

class EndorsementCreate(BaseModel):
    researcher_id: uuid.UUID
    subject_area: str = Field(..., max_length=200)
    endorsement_text: Optional[str] = None


class EndorsementResponse(BaseModel):
    id: uuid.UUID
    professor_id: uuid.UUID
    researcher_id: uuid.UUID
    subject_area: str
    endorsement_text: Optional[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Course Assignment
# ─────────────────────────────────────────────────────────────────────────────

class AssignmentCreate(BaseModel):
    title: str = Field(..., min_length=5, max_length=300)
    description: str = Field(..., min_length=20)
    subject: str = Field(..., max_length=200)
    academic_level: Optional[str] = Field(None, max_length=100)
    rubric: Optional[str] = None
    min_quality_score: Optional[int] = Field(None, ge=0, le=100)
    review_required: bool = False
    suggested_price: Optional[float] = Field(None, gt=0)
    deadline_hours: Optional[int] = Field(None, gt=0, le=336)
    is_active: bool = True


class AssignmentUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=300)
    description: Optional[str] = None
    rubric: Optional[str] = None
    min_quality_score: Optional[int] = Field(None, ge=0, le=100)
    review_required: Optional[bool] = None
    suggested_price: Optional[float] = None
    deadline_hours: Optional[int] = None
    is_active: Optional[bool] = None


class AssignmentResponse(BaseModel):
    id: uuid.UUID
    professor_id: uuid.UUID
    title: str
    description: str
    subject: str
    academic_level: Optional[str]
    rubric: Optional[str]
    min_quality_score: Optional[int]
    review_required: bool
    suggested_price: Optional[float]
    deadline_hours: Optional[int]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Quality Review
# ─────────────────────────────────────────────────────────────────────────────

class QualityReviewSubmit(BaseModel):
    score: int = Field(..., ge=0, le=100)
    originality_score: Optional[int] = Field(None, ge=0, le=100)
    feedback: str = Field(..., min_length=50)
    rubric_scores: Optional[dict] = None
    verdict: str = Field(
        ...,
        description="approved | revision_required | rejected",
    )


class QualityReviewResponse(BaseModel):
    id: uuid.UUID
    contract_id: uuid.UUID
    professor_id: uuid.UUID
    assignment_id: Optional[uuid.UUID]
    submission_id: Optional[uuid.UUID]
    round_number: int
    status: str
    score: Optional[int]
    originality_score: Optional[int]
    feedback: Optional[str]
    payment_held: bool
    reviewed_at: Optional[datetime]
    fee_amount: float
    fee_paid: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Dispute Ruling
# ─────────────────────────────────────────────────────────────────────────────

class DisputeRulingSubmit(BaseModel):
    ruling: str = Field(
        ...,
        description="full_release | partial_release | full_refund | revision",
    )
    release_percentage: Optional[float] = Field(
        None, ge=0, le=100,
        description="Required when ruling=partial_release"
    )
    reasoning: str = Field(..., min_length=100)
    evidence_reviewed: Optional[str] = None


class DisputeRulingResponse(BaseModel):
    id: uuid.UUID
    dispute_id: uuid.UUID
    professor_id: uuid.UUID
    ruling: str
    release_percentage: Optional[float]
    reasoning: str
    evidence_reviewed: Optional[str]
    submitted_at: Optional[datetime]
    overridden_by: Optional[uuid.UUID]
    override_reason: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Review Queue
# ─────────────────────────────────────────────────────────────────────────────

class ReviewQueueItemResponse(BaseModel):
    id: uuid.UUID
    contract_id: uuid.UUID
    professor_id: Optional[uuid.UUID]
    queue_type: str
    status: str
    priority: int
    sla_hours: int
    due_at: Optional[datetime]
    assigned_at: Optional[datetime]
    completed_at: Optional[datetime]
    notes: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Professor Analytics
# ─────────────────────────────────────────────────────────────────────────────

class ProfessorAnalytics(BaseModel):
    total_reviews: int
    pending_reviews: int
    completed_reviews: int
    avg_score_given: float
    total_fees_earned: float
    disputes_arbitrated: int
    credentials_verified: int
    endorsements_given: int
    sla_compliance_rate: float  # % reviews completed within SLA
