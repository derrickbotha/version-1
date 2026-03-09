
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.job import Job
from app.schemas.job_schema import JobCreate, JobFilterParams, JobUpdate
from app.utils.security import sanitize_input

_EDITABLE_STATUSES = ("draft", "open")
_DELETABLE_STATUSES = ("draft", "open")


def create_job(db: Session, student_id: uuid.UUID, data: JobCreate) -> Job:
    """
    Create a new job for the given student.

    All text fields are sanitized before persistence.
    The job is created with status='open'.
    """
    job = Job(
        id=uuid.uuid4(),
        student_id=student_id,
        title=sanitize_input(data.title),
        description=sanitize_input(data.description),
        subject=sanitize_input(data.subject),
        academic_level=sanitize_input(data.academic_level),
        proposed_price=data.proposed_price,
        status="open",
        deadline=data.deadline,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_jobs(
    db: Session,
    filters: JobFilterParams,
) -> tuple[list[Job], int]:
    """
    Return a paginated list of non-deleted jobs matching the given filters.

    Returns a tuple of (items, total_count).
    """
    query = db.query(Job).filter(Job.deleted_at.is_(None))

    if filters.status is not None:
        query = query.filter(Job.status == filters.status)

    if filters.subject is not None:
        query = query.filter(Job.subject.ilike(f"%{filters.subject}%"))

    if filters.min_price is not None:
        query = query.filter(Job.proposed_price >= filters.min_price)

    if filters.max_price is not None:
        query = query.filter(Job.proposed_price <= filters.max_price)

    total: int = query.count()

    offset = (filters.page - 1) * filters.page_size
    items: list[Job] = (
        query.order_by(Job.created_at.desc())
        .offset(offset)
        .limit(filters.page_size)
        .all()
    )
    return items, total


def get_job_by_id(db: Session, job_id: uuid.UUID) -> Job:
    """
    Fetch a single job by primary key.

    Raises:
        HTTPException 404 — if the job does not exist or has been soft-deleted.
    """
    job: Job | None = (
        db.query(Job)
        .filter(Job.id == job_id, Job.deleted_at.is_(None))
        .first()
    )
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )
    return job


def update_job(
    db: Session,
    job_id: uuid.UUID,
    student_id: uuid.UUID,
    data: JobUpdate,
) -> Job:
    """
    Update editable fields on a job.

    Only the owning student may update a job, and only when the job is in
    'draft' or 'open' status. Only fields explicitly provided (non-None) are
    updated.

    Raises:
        HTTPException 404 — job not found or deleted.
        HTTPException 403 — caller is not the job owner.
        HTTPException 400 — job is not in an editable status.
    """
    job = get_job_by_id(db, job_id)

    if job.student_id != student_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update this job",
        )

    if job.status not in _EDITABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Job cannot be updated in its current status '{job.status}'. "
                f"Allowed statuses: {', '.join(_EDITABLE_STATUSES)}"
            ),
        )

    update_data: dict[str, Any] = data.model_dump(exclude_none=True)

    text_fields = {"title", "description", "subject", "academic_level"}
    for field, value in update_data.items():
        if field in text_fields:
            setattr(job, field, sanitize_input(value))
        else:
            setattr(job, field, value)

    db.commit()
    db.refresh(job)
    return job


def delete_job(
    db: Session,
    job_id: uuid.UUID,
    student_id: uuid.UUID,
) -> None:
    """
    Soft-delete a job by setting deleted_at to the current UTC time.

    Only the owning student may delete a job, and only when the job is in
    'draft' or 'open' status.

    Raises:
        HTTPException 404 — job not found or already deleted.
        HTTPException 403 — caller is not the job owner.
        HTTPException 400 — job is not in a deletable status.
    """
    job = get_job_by_id(db, job_id)

    if job.student_id != student_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this job",
        )

    if job.status not in _DELETABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Job cannot be deleted in its current status '{job.status}'. "
                f"Allowed statuses: {', '.join(_DELETABLE_STATUSES)}"
            ),
        )

    job.deleted_at = datetime.now(timezone.utc)
    db.commit()


def get_student_jobs(
    db: Session,
    student_id: uuid.UUID,
    page: int,
    page_size: int,
) -> tuple[list[Job], int]:
    """
    Return a paginated list of all non-deleted jobs belonging to the given student.

    Returns a tuple of (items, total_count).
    """
    query = (
        db.query(Job)
        .filter(Job.student_id == student_id, Job.deleted_at.is_(None))
    )
    total: int = query.count()
    offset = (page - 1) * page_size
    items: list[Job] = (
        query.order_by(Job.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    return items, total


def transition_job_status(
    db: Session,
    job_id: uuid.UUID,
    new_status: str,
    allowed_from: list[str],
) -> Job:
    """
    Transition a job to a new status, validating that the current status is
    one of the allowed source statuses.

    Raises:
        HTTPException 404 — job not found or deleted.
        HTTPException 400 — transition is not permitted from the current status.
    """
    job = get_job_by_id(db, job_id)

    if job.status not in allowed_from:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot transition job from '{job.status}' to '{new_status}'. "
                f"Allowed source statuses: {', '.join(allowed_from)}"
            ),
        )

    job.status = new_status
    db.commit()
    db.refresh(job)
    return job
