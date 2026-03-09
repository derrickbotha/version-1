"""
Professor service — business logic for all professor-facing operations.

Covers:
  - Profile creation & updates
  - Credential verification queue
  - Endorsement management
  - Course assignment templates
  - Quality review workflow (the core professor function)
  - Dispute ruling
  - Review queue management & SLA tracking
  - Professor analytics
"""

import datetime as _dt
import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.contract import Contract, Dispute
from app.models.professor import (
    CourseAssignment,
    DisputeRuling,
    Institution,
    PlatformConfig,
    ProfessorEndorsement,
    ProfessorProfile,
    QualityReview,
    ResearcherCredential,
    ReviewQueueItem,
)
from app.models.submission import Submission
from app.models.user import User
from app.schemas.professor_schema import (
    AssignmentCreate,
    AssignmentUpdate,
    CredentialSubmit,
    CredentialVerifyAction,
    DisputeRulingSubmit,
    EndorsementCreate,
    ProfessorAnalytics,
    ProfessorProfileCreate,
    ProfessorProfileUpdate,
    QualityReviewSubmit,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_professor_profile(db: Session, user_id: uuid.UUID) -> ProfessorProfile:
    prof = db.execute(
        select(ProfessorProfile).where(ProfessorProfile.user_id == user_id)
    ).scalar_one_or_none()
    if not prof:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Professor profile not found")
    return prof


def _require_approved(prof: ProfessorProfile) -> None:
    if prof.status != "approved":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Professor account is not yet approved (status: {prof.status})",
        )


# ─────────────────────────────────────────────────────────────────────────────
# Profile
# ─────────────────────────────────────────────────────────────────────────────

def create_professor_profile(
    db: Session, user: User, data: ProfessorProfileCreate
) -> ProfessorProfile:
    if user.role != "professor":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Only users with role='professor' can create a professor profile",
        )
    existing = db.execute(
        select(ProfessorProfile).where(ProfessorProfile.user_id == user.id)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Professor profile already exists")

    prof = ProfessorProfile(
        user_id=user.id,
        institution_id=data.institution_id,
        title=data.title,
        department=data.department,
        academic_rank=data.academic_rank,
        bio=data.bio,
        expertise_areas=data.expertise_areas or [],
        orcid_id=data.orcid_id,
        linkedin_url=data.linkedin_url,
        institutional_email=data.institutional_email,
        review_subjects=data.review_subjects or [],
        status="pending",
    )
    db.add(prof)
    db.commit()
    db.refresh(prof)
    return prof


def get_professor_profile(db: Session, user_id: uuid.UUID) -> ProfessorProfile:
    return _get_professor_profile(db, user_id)


def update_professor_profile(
    db: Session, user_id: uuid.UUID, data: ProfessorProfileUpdate
) -> ProfessorProfile:
    prof = _get_professor_profile(db, user_id)
    for field, val in data.model_dump(exclude_none=True).items():
        setattr(prof, field, val)
    db.commit()
    db.refresh(prof)
    return prof


# ─────────────────────────────────────────────────────────────────────────────
# Institutions
# ─────────────────────────────────────────────────────────────────────────────

def list_institutions(db: Session, verified_only: bool = True) -> list[Institution]:
    q = select(Institution)
    if verified_only:
        q = q.where(Institution.is_verified.is_(True))
    return list(db.execute(q.order_by(Institution.name)).scalars())


# ─────────────────────────────────────────────────────────────────────────────
# Credential Verification
# ─────────────────────────────────────────────────────────────────────────────

def submit_credential(
    db: Session, researcher: User, data: CredentialSubmit
) -> ResearcherCredential:
    if researcher.role not in ("researcher",):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Only researchers can submit credentials"
        )
    cred = ResearcherCredential(
        researcher_id=researcher.id,
        credential_type=data.credential_type,
        institution_name=data.institution_name,
        field_of_study=data.field_of_study,
        year_obtained=data.year_obtained,
        document_url=data.document_url,
        notes=data.notes,
        status="pending",
    )
    db.add(cred)
    db.commit()
    db.refresh(cred)
    return cred


def get_pending_credentials(db: Session, professor_user_id: uuid.UUID) -> list[ResearcherCredential]:
    prof = _get_professor_profile(db, professor_user_id)
    _require_approved(prof)
    return list(
        db.execute(
            select(ResearcherCredential)
            .where(ResearcherCredential.status == "pending")
            .order_by(ResearcherCredential.created_at)
        ).scalars()
    )


def action_credential(
    db: Session,
    credential_id: uuid.UUID,
    professor_user_id: uuid.UUID,
    data: CredentialVerifyAction,
) -> ResearcherCredential:
    prof = _get_professor_profile(db, professor_user_id)
    _require_approved(prof)

    cred = db.get(ResearcherCredential, credential_id)
    if not cred:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Credential not found")
    if cred.status != "pending":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Credential already actioned (status: {cred.status})",
        )

    if data.action == "verify":
        cred.status = "verified"
        cred.verified_by_id = prof.id
        cred.verified_at = _dt.datetime.now(_dt.timezone.utc)
    elif data.action == "reject":
        if not data.rejection_reason:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "rejection_reason is required when rejecting a credential",
            )
        cred.status = "rejected"
        cred.rejection_reason = data.rejection_reason
    else:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "action must be 'verify' or 'reject'",
        )

    db.commit()
    db.refresh(cred)
    return cred


def get_researcher_credentials(
    db: Session, researcher_id: uuid.UUID
) -> list[ResearcherCredential]:
    return list(
        db.execute(
            select(ResearcherCredential)
            .where(ResearcherCredential.researcher_id == researcher_id)
            .order_by(ResearcherCredential.created_at.desc())
        ).scalars()
    )


# ─────────────────────────────────────────────────────────────────────────────
# Endorsements
# ─────────────────────────────────────────────────────────────────────────────

def create_endorsement(
    db: Session, professor_user_id: uuid.UUID, data: EndorsementCreate
) -> ProfessorEndorsement:
    prof = _get_professor_profile(db, professor_user_id)
    _require_approved(prof)

    researcher = db.get(User, data.researcher_id)
    if not researcher or researcher.role != "researcher":
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Researcher not found"
        )

    existing = db.execute(
        select(ProfessorEndorsement).where(
            ProfessorEndorsement.professor_id == prof.id,
            ProfessorEndorsement.researcher_id == data.researcher_id,
            ProfessorEndorsement.subject_area == data.subject_area,
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "You have already endorsed this researcher for this subject area",
        )

    endorsement = ProfessorEndorsement(
        professor_id=prof.id,
        researcher_id=data.researcher_id,
        subject_area=data.subject_area,
        endorsement_text=data.endorsement_text,
        is_active=True,
    )
    db.add(endorsement)
    db.commit()
    db.refresh(endorsement)
    return endorsement


def get_endorsements_for_researcher(
    db: Session, researcher_id: uuid.UUID
) -> list[ProfessorEndorsement]:
    return list(
        db.execute(
            select(ProfessorEndorsement)
            .where(
                ProfessorEndorsement.researcher_id == researcher_id,
                ProfessorEndorsement.is_active.is_(True),
            )
            .options(selectinload(ProfessorEndorsement.professor))
        ).scalars()
    )


def revoke_endorsement(
    db: Session, endorsement_id: uuid.UUID, professor_user_id: uuid.UUID
) -> None:
    prof = _get_professor_profile(db, professor_user_id)
    end = db.get(ProfessorEndorsement, endorsement_id)
    if not end or end.professor_id != prof.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Endorsement not found")
    end.is_active = False
    db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Course Assignments
# ─────────────────────────────────────────────────────────────────────────────

def create_assignment(
    db: Session, professor_user_id: uuid.UUID, data: AssignmentCreate
) -> CourseAssignment:
    prof = _get_professor_profile(db, professor_user_id)
    _require_approved(prof)

    assignment = CourseAssignment(
        professor_id=prof.id,
        title=data.title,
        description=data.description,
        subject=data.subject,
        academic_level=data.academic_level,
        rubric=data.rubric,
        min_quality_score=data.min_quality_score,
        review_required=data.review_required,
        suggested_price=data.suggested_price,
        deadline_hours=data.deadline_hours,
        is_active=data.is_active,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def list_assignments(
    db: Session, professor_user_id: uuid.UUID
) -> list[CourseAssignment]:
    prof = _get_professor_profile(db, professor_user_id)
    return list(
        db.execute(
            select(CourseAssignment)
            .where(CourseAssignment.professor_id == prof.id)
            .order_by(CourseAssignment.created_at.desc())
        ).scalars()
    )


def update_assignment(
    db: Session,
    assignment_id: uuid.UUID,
    professor_user_id: uuid.UUID,
    data: AssignmentUpdate,
) -> CourseAssignment:
    prof = _get_professor_profile(db, professor_user_id)
    assignment = db.get(CourseAssignment, assignment_id)
    if not assignment or assignment.professor_id != prof.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Assignment not found")

    for field, val in data.model_dump(exclude_none=True).items():
        setattr(assignment, field, val)
    db.commit()
    db.refresh(assignment)
    return assignment


def delete_assignment(
    db: Session, assignment_id: uuid.UUID, professor_user_id: uuid.UUID
) -> None:
    prof = _get_professor_profile(db, professor_user_id)
    assignment = db.get(CourseAssignment, assignment_id)
    if not assignment or assignment.professor_id != prof.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Assignment not found")
    assignment.is_active = False   # soft delete
    db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Review Queue
# ─────────────────────────────────────────────────────────────────────────────

def get_my_queue(
    db: Session, professor_user_id: uuid.UUID, status_filter: Optional[str] = None
) -> list[ReviewQueueItem]:
    prof = _get_professor_profile(db, professor_user_id)
    _require_approved(prof)

    q = select(ReviewQueueItem).where(ReviewQueueItem.professor_id == prof.id)
    if status_filter:
        q = q.where(ReviewQueueItem.status == status_filter)
    return list(db.execute(q.order_by(ReviewQueueItem.priority, ReviewQueueItem.due_at)).scalars())


def _get_queue_item(db: Session, item_id: uuid.UUID) -> ReviewQueueItem:
    item = db.get(ReviewQueueItem, item_id)
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Queue item not found")
    return item


def accept_queue_item(
    db: Session, item_id: uuid.UUID, professor_user_id: uuid.UUID
) -> ReviewQueueItem:
    """Professor marks a queue item as in_progress (starts the clock)."""
    prof = _get_professor_profile(db, professor_user_id)
    item = _get_queue_item(db, item_id)

    if item.professor_id != prof.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This item is not assigned to you")
    if item.status not in ("queued", "assigned"):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Cannot accept item with status={item.status}"
        )

    item.status = "in_progress"
    item.assigned_at = _dt.datetime.now(_dt.timezone.utc)
    db.commit()
    db.refresh(item)
    return item


# ─────────────────────────────────────────────────────────────────────────────
# Quality Reviews
# ─────────────────────────────────────────────────────────────────────────────

def submit_quality_review(
    db: Session,
    contract_id: uuid.UUID,
    professor_user_id: uuid.UUID,
    data: QualityReviewSubmit,
) -> QualityReview:
    prof = _get_professor_profile(db, professor_user_id)
    _require_approved(prof)

    contract = db.get(Contract, contract_id)
    if not contract:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contract not found")
    if contract.status not in ("submitted", "revision_requested", "in_progress"):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Contract status '{contract.status}' is not reviewable",
        )

    # Determine round number
    existing_rounds = db.execute(
        select(func.count()).where(QualityReview.contract_id == contract_id)
    ).scalar() or 0
    round_number = existing_rounds + 1

    # Map verdict to review status
    status_map = {
        "approved": "approved",
        "revision_required": "revision_required",
        "rejected": "rejected",
    }
    if data.verdict not in status_map:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "verdict must be: approved | revision_required | rejected"
        )

    review = QualityReview(
        contract_id=contract_id,
        professor_id=prof.id,
        round_number=round_number,
        status=status_map[data.verdict],
        score=data.score,
        originality_score=data.originality_score,
        feedback=data.feedback,
        rubric_scores=str(data.rubric_scores) if data.rubric_scores else None,
        reviewed_at=_dt.datetime.now(_dt.timezone.utc),
        fee_amount=prof.review_fee_per_job,
        fee_paid=False,
    )
    db.add(review)

    # Update contract status based on verdict
    if data.verdict == "approved":
        contract.status = "completed"
    elif data.verdict == "revision_required":
        contract.status = "revision_requested"
    elif data.verdict == "rejected":
        # Contract goes back to disputed for admin financial resolution
        contract.status = "disputed"

    # Update professor stats
    prof.total_reviews_completed += 1
    current_avg = float(prof.avg_review_score_given or 0)
    total = prof.total_reviews_completed
    prof.avg_review_score_given = (
        (current_avg * (total - 1) + data.score) / total
    )

    # Mark queue item completed
    db.execute(
        select(ReviewQueueItem)
        .where(
            ReviewQueueItem.contract_id == contract_id,
            ReviewQueueItem.professor_id == prof.id,
            ReviewQueueItem.status == "in_progress",
        )
    )
    queue_item = db.execute(
        select(ReviewQueueItem).where(
            ReviewQueueItem.contract_id == contract_id,
            ReviewQueueItem.professor_id == prof.id,
            ReviewQueueItem.status == "in_progress",
        )
    ).scalar_one_or_none()
    if queue_item:
        queue_item.status = "completed"
        queue_item.completed_at = _dt.datetime.now(_dt.timezone.utc)

    db.commit()
    db.refresh(review)
    return review


def get_reviews_by_professor(
    db: Session, professor_user_id: uuid.UUID
) -> list[QualityReview]:
    prof = _get_professor_profile(db, professor_user_id)
    return list(
        db.execute(
            select(QualityReview)
            .where(QualityReview.professor_id == prof.id)
            .order_by(QualityReview.reviewed_at.desc())
        ).scalars()
    )


def get_contract_review(
    db: Session, contract_id: uuid.UUID
) -> list[QualityReview]:
    return list(
        db.execute(
            select(QualityReview)
            .where(QualityReview.contract_id == contract_id)
            .order_by(QualityReview.round_number)
        ).scalars()
    )


# ─────────────────────────────────────────────────────────────────────────────
# Dispute Rulings
# ─────────────────────────────────────────────────────────────────────────────

def get_assigned_disputes(
    db: Session, professor_user_id: uuid.UUID
) -> list[ReviewQueueItem]:
    prof = _get_professor_profile(db, professor_user_id)
    _require_approved(prof)
    return list(
        db.execute(
            select(ReviewQueueItem).where(
                ReviewQueueItem.professor_id == prof.id,
                ReviewQueueItem.queue_type == "dispute_arbitration",
                ReviewQueueItem.status.in_(("assigned", "in_progress")),
            )
        ).scalars()
    )


def submit_dispute_ruling(
    db: Session,
    dispute_id: uuid.UUID,
    professor_user_id: uuid.UUID,
    data: DisputeRulingSubmit,
) -> DisputeRuling:
    prof = _get_professor_profile(db, professor_user_id)
    _require_approved(prof)

    dispute = db.get(Dispute, dispute_id)
    if not dispute:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dispute not found")
    if dispute.status not in ("open", "investigating"):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Dispute status '{dispute.status}' cannot accept a ruling",
        )

    # Guard: partial_release requires a percentage
    if data.ruling == "partial_release" and data.release_percentage is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "release_percentage is required for partial_release ruling",
        )

    existing_ruling = db.execute(
        select(DisputeRuling).where(DisputeRuling.dispute_id == dispute_id)
    ).scalar_one_or_none()
    if existing_ruling:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "A ruling already exists for this dispute"
        )

    ruling = DisputeRuling(
        dispute_id=dispute_id,
        professor_id=prof.id,
        ruling=data.ruling,
        release_percentage=data.release_percentage,
        reasoning=data.reasoning,
        evidence_reviewed=data.evidence_reviewed,
        submitted_at=_dt.datetime.now(_dt.timezone.utc),
    )
    db.add(ruling)
    dispute.status = "investigating"  # Admin must now execute the ruling

    db.commit()
    db.refresh(ruling)
    return ruling


# ─────────────────────────────────────────────────────────────────────────────
# Analytics
# ─────────────────────────────────────────────────────────────────────────────

def get_professor_analytics(
    db: Session, professor_user_id: uuid.UUID
) -> ProfessorAnalytics:
    prof = _get_professor_profile(db, professor_user_id)

    total_reviews = db.execute(
        select(func.count()).where(QualityReview.professor_id == prof.id)
    ).scalar() or 0

    pending_reviews = db.execute(
        select(func.count()).where(
            QualityReview.professor_id == prof.id,
            QualityReview.status == "pending",
        )
    ).scalar() or 0

    completed_reviews = db.execute(
        select(func.count()).where(
            QualityReview.professor_id == prof.id,
            QualityReview.status.in_(("approved", "revision_required", "rejected")),
        )
    ).scalar() or 0

    total_fees = db.execute(
        select(func.sum(QualityReview.fee_amount)).where(
            QualityReview.professor_id == prof.id,
            QualityReview.fee_paid.is_(True),
        )
    ).scalar() or 0.0

    disputes_arbitrated = db.execute(
        select(func.count()).where(
            DisputeRuling.professor_id == prof.id
        )
    ).scalar() or 0

    credentials_verified = db.execute(
        select(func.count()).where(
            ResearcherCredential.verified_by_id == prof.id,
            ResearcherCredential.status == "verified",
        )
    ).scalar() or 0

    endorsements_given = db.execute(
        select(func.count()).where(
            ProfessorEndorsement.professor_id == prof.id,
            ProfessorEndorsement.is_active.is_(True),
        )
    ).scalar() or 0

    # SLA compliance: completed queue items vs total assigned
    total_assigned = db.execute(
        select(func.count()).where(
            ReviewQueueItem.professor_id == prof.id,
            ReviewQueueItem.status.in_(("completed", "expired")),
        )
    ).scalar() or 1  # avoid division by zero

    completed_on_time = db.execute(
        select(func.count()).where(
            ReviewQueueItem.professor_id == prof.id,
            ReviewQueueItem.status == "completed",
            ReviewQueueItem.completed_at <= ReviewQueueItem.due_at,
        )
    ).scalar() or 0

    sla_rate = round((completed_on_time / total_assigned) * 100, 1)

    return ProfessorAnalytics(
        total_reviews=total_reviews,
        pending_reviews=pending_reviews,
        completed_reviews=completed_reviews,
        avg_score_given=float(prof.avg_review_score_given or 0),
        total_fees_earned=float(total_fees),
        disputes_arbitrated=disputes_arbitrated,
        credentials_verified=credentials_verified,
        endorsements_given=endorsements_given,
        sla_compliance_rate=sla_rate,
    )
