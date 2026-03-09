
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.audit_log import AuditLog
from app.models.user import User
from app.services import admin_service
from app.utils.jwt_handler import require_role

router = APIRouter(prefix="/admin", tags=["Admin"])

_admin_dep = Depends(require_role("admin"))


def _serialize_user(user: User) -> dict:
    """Return a JSON-serialisable dict for a User ORM instance."""
    return {
        "id": str(user.id),
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.role,
        "status": user.status,
        "is_verified": user.is_verified,
        "created_at": user.created_at.isoformat(),
    }


def _serialize_job(job) -> dict:
    """Return a JSON-serialisable dict for a Job ORM instance."""
    return {
        "id": str(job.id),
        "student_id": str(job.student_id),
        "title": job.title,
        "subject": job.subject,
        "academic_level": job.academic_level,
        "proposed_price": float(job.proposed_price),
        "status": job.status,
        "deadline": job.deadline.isoformat() if job.deadline else None,
        "created_at": job.created_at.isoformat(),
    }


def _serialize_audit_log(entry: AuditLog) -> dict:
    """Return a JSON-serialisable dict for an AuditLog ORM instance."""
    return {
        "id": str(entry.id),
        "admin_id": str(entry.admin_id) if entry.admin_id else None,
        "action": entry.action,
        "entity_type": entry.entity_type,
        "entity_id": str(entry.entity_id) if entry.entity_id else None,
        "details": entry.details,
        "created_at": entry.created_at.isoformat(),
    }


@router.get(
    "/users",
    response_model=dict,
    summary="List all users (admin only)",
)
def list_users(
    role: str | None = Query(default=None, description="Filter by role"),
    user_status: str | None = Query(
        default=None,
        alias="status",
        description="Filter by status",
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = _admin_dep,
    db: Session = Depends(get_db),
) -> dict:
    """List all registered users, paginated, with optional role/status filters."""
    users, total = admin_service.get_users(
        db=db,
        role=role,
        user_status=user_status,
        page=page,
        page_size=page_size,
    )
    return {
        "status": "success",
        "data": {
            "items": [_serialize_user(u) for u in users],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }


@router.patch(
    "/users/{user_id}/suspend",
    response_model=dict,
    summary="Suspend a user (admin only)",
)
def suspend_user(
    user_id: uuid.UUID,
    current_user: User = _admin_dep,
    db: Session = Depends(get_db),
) -> dict:
    """Suspend a user account, preventing them from logging in."""
    admin_service.suspend_user(db=db, user_id=user_id, admin_id=current_user.id)
    return {
        "status": "success",
        "data": {"message": f"User {user_id} has been suspended"},
    }


@router.patch(
    "/users/{user_id}/activate",
    response_model=dict,
    summary="Activate a user (admin only)",
)
def activate_user(
    user_id: uuid.UUID,
    current_user: User = _admin_dep,
    db: Session = Depends(get_db),
) -> dict:
    """Re-activate a previously suspended user account."""
    admin_service.activate_user(db=db, user_id=user_id, admin_id=current_user.id)
    return {
        "status": "success",
        "data": {"message": f"User {user_id} has been activated"},
    }


@router.get(
    "/jobs",
    response_model=dict,
    summary="List all jobs (admin only)",
)
def list_all_jobs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = _admin_dep,
    db: Session = Depends(get_db),
) -> dict:
    """List all jobs across all statuses, paginated."""
    from app.models.job import Job  # noqa: PLC0415

    query = db.query(Job).order_by(Job.created_at.desc())
    total: int = query.count()
    offset = (page - 1) * page_size
    jobs = query.offset(offset).limit(page_size).all()

    return {
        "status": "success",
        "data": {
            "items": [_serialize_job(j) for j in jobs],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }


@router.get(
    "/stats",
    response_model=dict,
    summary="Get platform statistics (admin only)",
)
def get_stats(
    current_user: User = _admin_dep,
    db: Session = Depends(get_db),
) -> dict:
    """
    Return aggregate platform statistics:

    - Total users broken down by role.
    - Total jobs broken down by status.
    - Total payment volume (sum of all payments).
    - Count of open and investigating disputes.
    """
    stats = admin_service.get_platform_stats(db=db)
    return {"status": "success", "data": stats}


@router.get(
    "/audit-log",
    response_model=dict,
    summary="List audit log entries (admin only)",
)
def list_audit_log(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = _admin_dep,
    db: Session = Depends(get_db),
) -> dict:
    """Return paginated audit log entries, newest first."""
    query = db.query(AuditLog).order_by(AuditLog.created_at.desc())
    total: int = query.count()
    offset = (page - 1) * page_size
    entries = query.offset(offset).limit(page_size).all()

    return {
        "status": "success",
        "data": {
            "items": [_serialize_audit_log(e) for e in entries],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }
