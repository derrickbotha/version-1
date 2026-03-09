"""
Professor API router — /api/v1/professor/*

All endpoints require JWT authentication.
Role-restricted endpoints require role='professor' (or admin override).
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.schemas.professor_schema import (
    AssignmentCreate,
    AssignmentResponse,
    AssignmentUpdate,
    CredentialResponse,
    CredentialSubmit,
    CredentialVerifyAction,
    DisputeRulingResponse,
    DisputeRulingSubmit,
    EndorsementCreate,
    EndorsementResponse,
    InstitutionCreate,
    InstitutionResponse,
    ProfessorAnalytics,
    ProfessorProfileCreate,
    ProfessorProfileResponse,
    ProfessorProfileUpdate,
    QualityReviewResponse,
    QualityReviewSubmit,
    ReviewQueueItemResponse,
)
from app.services import professor_service
from app.utils.jwt_handler import get_current_user, require_role

router = APIRouter(prefix="/professor", tags=["Professor"])


# ─────────────────────────────────────────────────────────────────────────────
# Institutions (public read, admin-only write)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/institutions", response_model=list[InstitutionResponse])
def list_institutions(
    verified_only: bool = Query(True),
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """List verified academic institutions."""
    return professor_service.list_institutions(db, verified_only=verified_only)


# ─────────────────────────────────────────────────────────────────────────────
# Professor Profile
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/profile", response_model=ProfessorProfileResponse, status_code=201)
def create_profile(
    data: ProfessorProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("professor")),
):
    """
    Create a professor profile.  Requires the user's role to already be 'professor'
    (set by an admin using POST /admin/users/{id}/role).
    Profile starts in 'pending' status until approved by an admin.
    """
    return professor_service.create_professor_profile(db, current_user, data)


@router.get("/profile", response_model=ProfessorProfileResponse)
def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("professor")),
):
    """Get the authenticated professor's profile."""
    return professor_service.get_professor_profile(db, current_user.id)


@router.patch("/profile", response_model=ProfessorProfileResponse)
def update_profile(
    data: ProfessorProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("professor")),
):
    """Update professor profile details."""
    return professor_service.update_professor_profile(db, current_user.id, data)


# ─────────────────────────────────────────────────────────────────────────────
# Credential Verification
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/credentials", response_model=CredentialResponse, status_code=201)
def submit_credential(
    data: CredentialSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("researcher")),
):
    """
    Researcher submits an academic credential for professor verification.
    Uploaded document URL should be a pre-signed S3 URL from the file upload endpoint.
    """
    return professor_service.submit_credential(db, current_user, data)


@router.get("/credentials/pending", response_model=list[CredentialResponse])
def get_pending_credentials(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("professor")),
):
    """Professor views credentials awaiting their review."""
    return professor_service.get_pending_credentials(db, current_user.id)


@router.post("/credentials/{credential_id}/action", response_model=CredentialResponse)
def action_credential(
    credential_id: uuid.UUID,
    data: CredentialVerifyAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("professor")),
):
    """Professor verifies or rejects a submitted credential."""
    return professor_service.action_credential(db, credential_id, current_user.id, data)


@router.get("/credentials/researcher/{researcher_id}", response_model=list[CredentialResponse])
def get_researcher_credentials(
    researcher_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Public: get all credentials for a specific researcher."""
    return professor_service.get_researcher_credentials(db, researcher_id)


# ─────────────────────────────────────────────────────────────────────────────
# Endorsements
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/endorsements", response_model=EndorsementResponse, status_code=201)
def create_endorsement(
    data: EndorsementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("professor")),
):
    """Professor endorses a researcher for a subject area."""
    return professor_service.create_endorsement(db, current_user.id, data)


@router.get("/endorsements/researcher/{researcher_id}", response_model=list[EndorsementResponse])
def get_endorsements(
    researcher_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Get all active endorsements for a researcher."""
    return professor_service.get_endorsements_for_researcher(db, researcher_id)


@router.delete("/endorsements/{endorsement_id}", status_code=204)
def revoke_endorsement(
    endorsement_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("professor")),
):
    """Professor revokes an endorsement."""
    professor_service.revoke_endorsement(db, endorsement_id, current_user.id)


# ─────────────────────────────────────────────────────────────────────────────
# Course Assignments
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/assignments", response_model=AssignmentResponse, status_code=201)
def create_assignment(
    data: AssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("professor")),
):
    """
    Create a course assignment template.
    Students in the professor's course can use this to quickly post a job
    with pre-filled details and a rubric.
    """
    return professor_service.create_assignment(db, current_user.id, data)


@router.get("/assignments", response_model=list[AssignmentResponse])
def list_assignments(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("professor")),
):
    """List all assignments created by the authenticated professor."""
    return professor_service.list_assignments(db, current_user.id)


@router.patch("/assignments/{assignment_id}", response_model=AssignmentResponse)
def update_assignment(
    assignment_id: uuid.UUID,
    data: AssignmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("professor")),
):
    """Update an assignment template."""
    return professor_service.update_assignment(db, assignment_id, current_user.id, data)


@router.delete("/assignments/{assignment_id}", status_code=204)
def delete_assignment(
    assignment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("professor")),
):
    """Soft-delete (deactivate) an assignment template."""
    professor_service.delete_assignment(db, assignment_id, current_user.id)


# ─────────────────────────────────────────────────────────────────────────────
# Review Queue
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/queue", response_model=list[ReviewQueueItemResponse])
def get_queue(
    status_filter: str = Query(None, description="queued|assigned|in_progress|completed"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("professor")),
):
    """Get the professor's current review queue."""
    return professor_service.get_my_queue(db, current_user.id, status_filter)


@router.post("/queue/{item_id}/accept", response_model=ReviewQueueItemResponse)
def accept_queue_item(
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("professor")),
):
    """Accept a queue item and mark it as in_progress (starts the SLA clock)."""
    return professor_service.accept_queue_item(db, item_id, current_user.id)


# ─────────────────────────────────────────────────────────────────────────────
# Quality Reviews
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/reviews/contract/{contract_id}", response_model=QualityReviewResponse, status_code=201)
def submit_review(
    contract_id: uuid.UUID,
    data: QualityReviewSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("professor")),
):
    """
    Submit a quality review for a contract's submitted work.

    Verdicts:
      - approved: work meets standards → contract moves to 'completed'
      - revision_required: work needs improvement → contract reverts to 'revision_requested'
      - rejected: work is unacceptable → contract moves to 'disputed' for admin resolution

    Score: 0–100 (maps to A/B/C/D/F grade bands)
    Originality: 0–100 (100 = fully original, 0 = complete plagiarism)
    """
    return professor_service.submit_quality_review(db, contract_id, current_user.id, data)


@router.get("/reviews", response_model=list[QualityReviewResponse])
def get_my_reviews(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("professor")),
):
    """List all quality reviews submitted by the professor."""
    return professor_service.get_reviews_by_professor(db, current_user.id)


@router.get("/reviews/contract/{contract_id}", response_model=list[QualityReviewResponse])
def get_contract_reviews(
    contract_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Get all quality reviews for a specific contract (visible to all parties)."""
    return professor_service.get_contract_review(db, contract_id)


# ─────────────────────────────────────────────────────────────────────────────
# Dispute Arbitration
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/disputes", response_model=list[ReviewQueueItemResponse])
def get_assigned_disputes(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("professor")),
):
    """Get disputes assigned to this professor for academic arbitration."""
    return professor_service.get_assigned_disputes(db, current_user.id)


@router.post("/disputes/{dispute_id}/ruling", response_model=DisputeRulingResponse, status_code=201)
def submit_ruling(
    dispute_id: uuid.UUID,
    data: DisputeRulingSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("professor")),
):
    """
    Submit an academic ruling on a dispute.

    The ruling is binding unless overridden by a super_admin.
    The admin then executes the financial outcome (payment release/refund).

    Rulings:
      - full_release: researcher delivered acceptable work → pay in full
      - partial_release: partial credit (specify release_percentage)
      - full_refund: work was inadequate → full refund to student
      - revision: one more revision round required
    """
    return professor_service.submit_dispute_ruling(db, dispute_id, current_user.id, data)


# ─────────────────────────────────────────────────────────────────────────────
# Analytics
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/analytics", response_model=ProfessorAnalytics)
def get_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("professor")),
):
    """Professor performance analytics dashboard."""
    return professor_service.get_professor_analytics(db, current_user.id)
