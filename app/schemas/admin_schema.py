"""Pydantic schemas for admin dashboard and management endpoints."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# User Management
# ─────────────────────────────────────────────────────────────────────────────

class AdminUserUpdate(BaseModel):
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    is_verified: Optional[bool] = None
    status: Optional[str] = Field(None, description="active | suspended | deleted")


class RoleAssignRequest(BaseModel):
    role: str = Field(
        ...,
        description="student | researcher | professor | admin | super_admin",
    )
    reason: Optional[str] = None


class SuspendRequest(BaseModel):
    reason: str = Field(..., min_length=10)
    duration_hours: Optional[int] = Field(
        None, description="None = indefinite suspension"
    )


class AdminUserResponse(BaseModel):
    id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    role: str
    status: str
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AdminUserDetail(AdminUserResponse):
    phone: Optional[str]
    whatsapp_number: Optional[str]
    failed_login_attempts: int
    locked_until: Optional[datetime]
    wallet_balance: Optional[float] = None
    total_jobs: Optional[int] = None
    total_contracts: Optional[int] = None


class AdminUserListResponse(BaseModel):
    users: list[AdminUserResponse]
    total: int
    page: int
    page_size: int


# ─────────────────────────────────────────────────────────────────────────────
# Professor Management (Admin)
# ─────────────────────────────────────────────────────────────────────────────

class ProfessorApproveRequest(BaseModel):
    action: str = Field(..., description="'approve' or 'reject'")
    reason: Optional[str] = None
    review_fee_override: Optional[float] = Field(
        None, ge=0, description="Override default review fee for this professor"
    )


class AdminProfessorResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    user_email: str
    user_name: str
    institution_name: Optional[str]
    department: Optional[str]
    academic_rank: Optional[str]
    status: str
    total_reviews_completed: int
    review_subjects: Optional[list[str]]
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Job / Contract Management
# ─────────────────────────────────────────────────────────────────────────────

class AdminJobResponse(BaseModel):
    id: uuid.UUID
    title: str
    subject: str
    status: str
    proposed_price: float
    student_id: uuid.UUID
    student_email: str
    created_at: datetime
    deadline: Optional[datetime]
    is_flagged: bool = False

    model_config = {"from_attributes": True}


class AdminContractResponse(BaseModel):
    id: uuid.UUID
    job_title: str
    student_email: str
    researcher_email: str
    agreed_price: float
    status: str
    start_date: Optional[datetime]
    deadline: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminContractListResponse(BaseModel):
    contracts: list[AdminContractResponse]
    total: int
    page: int
    page_size: int


# ─────────────────────────────────────────────────────────────────────────────
# Dispute Management
# ─────────────────────────────────────────────────────────────────────────────

class AssignProfessorRequest(BaseModel):
    professor_id: uuid.UUID
    notes: Optional[str] = None


class AdminDisputeResolve(BaseModel):
    resolution: str = Field(..., min_length=20)
    financial_action: str = Field(
        ...,
        description="full_release | partial_release | full_refund",
    )
    release_percentage: Optional[float] = Field(
        None, ge=0, le=100
    )


class AdminDisputeResponse(BaseModel):
    id: uuid.UUID
    contract_id: uuid.UUID
    job_title: str
    opened_by_email: str
    reason: str
    status: str
    professor_assigned: Optional[str] = None
    ruling: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Financial / Payout Management
# ─────────────────────────────────────────────────────────────────────────────

class PayoutApproveRequest(BaseModel):
    notes: Optional[str] = None


class PayoutRejectRequest(BaseModel):
    reason: str = Field(..., min_length=10)


class AdminPayoutResponse(BaseModel):
    id: uuid.UUID
    writer_id: uuid.UUID
    writer_email: str
    amount: float
    currency: str
    status: str
    provider: str
    requested_at: datetime
    processed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class AdminTransactionResponse(BaseModel):
    id: uuid.UUID
    user_email: str
    transaction_type: str
    amount: float
    reference_id: Optional[uuid.UUID]
    notes: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminTransactionListResponse(BaseModel):
    transactions: list[AdminTransactionResponse]
    total: int
    total_volume: float
    page: int
    page_size: int


# ─────────────────────────────────────────────────────────────────────────────
# Platform Config
# ─────────────────────────────────────────────────────────────────────────────

class ConfigUpdate(BaseModel):
    value: str = Field(..., min_length=1)
    description: Optional[str] = None


class ConfigResponse(BaseModel):
    key: str
    value: str
    description: Optional[str]
    updated_by: Optional[uuid.UUID]
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Analytics / Dashboard
# ─────────────────────────────────────────────────────────────────────────────

class PlatformOverview(BaseModel):
    # Users
    total_users: int
    active_users: int
    students: int
    researchers: int
    professors: int
    new_users_this_month: int

    # Jobs
    total_jobs: int
    open_jobs: int
    completed_jobs: int
    disputed_jobs: int

    # Revenue
    total_volume_usd: float
    platform_revenue_usd: float
    pending_payouts_usd: float

    # Quality
    avg_completion_rate: float       # % contracts that reach 'completed'
    avg_review_score: float          # avg professor quality score
    avg_dispute_resolution_hours: float


class RevenueBreakdown(BaseModel):
    period: str   # e.g. "2026-03"
    gross_volume: float
    platform_fee: float
    professor_fees: float
    payment_processor_fees: float
    net_revenue: float
    job_count: int


class UserGrowthPoint(BaseModel):
    date: str
    new_students: int
    new_researchers: int
    new_professors: int
    total_active: int


class JobMetrics(BaseModel):
    period: str
    jobs_posted: int
    jobs_completed: int
    jobs_disputed: int
    avg_price: float
    avg_completion_hours: float
    completion_rate: float


# ─────────────────────────────────────────────────────────────────────────────
# Audit Log
# ─────────────────────────────────────────────────────────────────────────────

class AuditLogResponse(BaseModel):
    id: uuid.UUID
    admin_id: uuid.UUID
    admin_email: str
    action: str
    entity_type: str
    entity_id: Optional[uuid.UUID]
    details: Optional[dict]
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    logs: list[AuditLogResponse]
    total: int
    page: int
    page_size: int
