
import uuid
from typing import Annotated, Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.schemas.job_schema import (
    JobCreate,
    JobFilterParams,
    JobListResponse,
    JobResponse,
    JobUpdate,
)
from app.services import job_service
from app.utils.jwt_handler import get_current_user, require_role

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post("", response_model=dict, status_code=201, summary="Create a new job")
def create_job(
    body: JobCreate,
    current_user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
) -> dict:
    """Create a new research job. Restricted to students."""
    job = job_service.create_job(db=db, student_id=current_user.id, data=body)
    return {
        "status": "success",
        "data": JobResponse.model_validate(job).model_dump(),
    }


@router.get("", response_model=dict, summary="List available jobs (public)")
def list_jobs(
    status: Annotated[Optional[str], Query(description="Filter by job status")] = None,
    subject: Annotated[Optional[str], Query(description="Filter by subject (partial match)")] = None,
    min_price: Annotated[Optional[Decimal], Query(description="Minimum proposed price")] = None,
    max_price: Annotated[Optional[Decimal], Query(description="Maximum proposed price")] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    db: Session = Depends(get_db),
) -> dict:
    """List open jobs with optional filters. No authentication required."""
    filters = JobFilterParams(
        status=status,
        subject=subject,
        min_price=min_price,
        max_price=max_price,
        page=page,
        page_size=page_size,
    )
    items, total = job_service.get_jobs(db=db, filters=filters)
    response = JobListResponse(
        items=[JobResponse.model_validate(j) for j in items],
        total=total,
        page=page,
        page_size=page_size,
    )
    return {"status": "success", "data": response.model_dump()}


@router.get("/mine", response_model=dict, summary="Get own jobs (student)")
def get_my_jobs(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    current_user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
) -> dict:
    """Return all jobs posted by the authenticated student."""
    items, total = job_service.get_student_jobs(
        db=db,
        student_id=current_user.id,
        page=page,
        page_size=page_size,
    )
    response = JobListResponse(
        items=[JobResponse.model_validate(j) for j in items],
        total=total,
        page=page,
        page_size=page_size,
    )
    return {"status": "success", "data": response.model_dump()}


@router.get("/{job_id}", response_model=dict, summary="Get job detail")
def get_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Fetch details for a specific job. Requires authentication."""
    job = job_service.get_job_by_id(db=db, job_id=job_id)
    return {
        "status": "success",
        "data": JobResponse.model_validate(job).model_dump(),
    }


@router.patch("/{job_id}", response_model=dict, summary="Update a job")
def update_job(
    job_id: uuid.UUID,
    body: JobUpdate,
    current_user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
) -> dict:
    """Update a job's fields. Only the owning student may update. Job must be draft or open."""
    job = job_service.update_job(
        db=db,
        job_id=job_id,
        student_id=current_user.id,
        data=body,
    )
    return {
        "status": "success",
        "data": JobResponse.model_validate(job).model_dump(),
    }


@router.delete("/{job_id}", response_model=dict, summary="Delete (soft) a job")
def delete_job(
    job_id: uuid.UUID,
    current_user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
) -> dict:
    """Soft-delete a job. Only the owning student may delete. Job must be draft or open."""
    job_service.delete_job(db=db, job_id=job_id, student_id=current_user.id)
    return {"status": "success", "data": {"message": "Job deleted successfully"}}
