from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.assignment import Assignment, Submission
from api.models.user import User
from api.schemas.assignment import AssignmentListResponse, AssignmentResponse, SubmissionResponse
from api.services.assignment_service import update_assignment_status
from api.services.auth_service import get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in ("admin", "professor"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or professor access required",
        )
    return current_user


@router.get("/assignments", response_model=AssignmentListResponse)
def admin_list_assignments(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    query = db.query(Assignment)
    if status_filter:
        query = query.filter(Assignment.status == status_filter)
    total = query.count()
    items = (
        query.order_by(Assignment.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return AssignmentListResponse(
        items=[AssignmentResponse.model_validate(a) for a in items],
        total=total,
        page=page,
        page_size=page_size,
    )


class ProfessorReviewBody(BaseModel):
    submission_id: UUID
    notes: str
    approved: bool = True


@router.put("/assignments/{assignment_id}/review", response_model=SubmissionResponse)
def professor_review(
    assignment_id: UUID,
    body: ProfessorReviewBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    submission = (
        db.query(Submission)
        .filter(
            Submission.id == body.submission_id,
            Submission.assignment_id == assignment_id,
        )
        .first()
    )
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    submission.professor_review_notes = body.notes
    submission.professor_reviewed_by = current_user.id

    if body.approved:
        # Move assignment to delivering state after professor approval
        assignment.status = "delivering"
    else:
        assignment.status = "qa"
        assignment.status_message = "Returned for revision after professor review"

    db.commit()
    db.refresh(submission)
    return SubmissionResponse.model_validate(submission)


@router.get("/metrics")
def get_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    total_assignments = db.query(func.count(Assignment.id)).scalar() or 0
    completed = (
        db.query(func.count(Assignment.id))
        .filter(Assignment.status == "completed")
        .scalar()
        or 0
    )
    failed = (
        db.query(func.count(Assignment.id))
        .filter(Assignment.status == "failed")
        .scalar()
        or 0
    )
    in_progress = (
        db.query(func.count(Assignment.id))
        .filter(Assignment.status.in_(["pending", "researching", "writing", "qa", "review", "delivering"]))
        .scalar()
        or 0
    )
    total_users = db.query(func.count(User.id)).filter(User.is_active.is_(True)).scalar() or 0
    total_submissions = db.query(func.count(Submission.id)).scalar() or 0
    plagiarism_passed = (
        db.query(func.count(Submission.id))
        .filter(Submission.plagiarism_score < 15)
        .scalar()
        or 0
    )

    # Average time saved (from research jobs)
    from api.models.assignment import ResearchJob

    avg_time_saved = (
        db.query(func.avg(ResearchJob.time_saved_minutes))
        .filter(ResearchJob.time_saved_minutes.isnot(None))
        .scalar()
    )

    return {
        "assignments": {
            "total": total_assignments,
            "completed": completed,
            "failed": failed,
            "in_progress": in_progress,
            "completion_rate_pct": round(completed / total_assignments * 100, 1)
            if total_assignments
            else 0,
        },
        "users": {
            "total_active": total_users,
        },
        "submissions": {
            "total": total_submissions,
            "plagiarism_passed_under_15_pct": plagiarism_passed,
        },
        "research": {
            "avg_time_saved_minutes": round(float(avg_time_saved), 1) if avg_time_saved else None,
        },
    }
