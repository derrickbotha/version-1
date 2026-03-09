
import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.contract import Contract, Dispute
from app.models.job import Job
from app.models.payment import Payment
from app.models.user import User


def log_admin_action(
    db: Session,
    admin_id: uuid.UUID,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None,
    details: dict | None,
) -> None:
    """Persist an admin action to the audit log."""
    entry = AuditLog(
        admin_id=admin_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
    )
    db.add(entry)
    # Caller is responsible for committing the session.


def get_users(
    db: Session,
    role: str | None,
    user_status: str | None,
    page: int,
    page_size: int,
) -> tuple[list[Any], int]:
    """
    Return a paginated list of users, optionally filtered by *role* and
    *user_status*, along with the total count.
    """
    query = db.query(User).order_by(User.created_at.desc())
    if role:
        query = query.filter(User.role == role)
    if user_status:
        query = query.filter(User.status == user_status)
    total: int = query.count()
    offset = (page - 1) * page_size
    items = query.offset(offset).limit(page_size).all()
    return items, total


def suspend_user(
    db: Session,
    user_id: uuid.UUID,
    admin_id: uuid.UUID,
) -> None:
    """
    Set a user's status to 'suspended' and log the action.

    Raises:
        HTTPException 404 — user not found.
        HTTPException 400 — user is already suspended or deleted.
    """
    user: User | None = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    if user.status == "suspended":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already suspended",
        )
    if user.status == "deleted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot suspend a deleted user",
        )

    user.status = "suspended"

    log_admin_action(
        db=db,
        admin_id=admin_id,
        action="suspend_user",
        entity_type="user",
        entity_id=user_id,
        details={"email": user.email, "previous_status": "active"},
    )

    db.commit()


def activate_user(
    db: Session,
    user_id: uuid.UUID,
    admin_id: uuid.UUID,
) -> None:
    """
    Set a user's status to 'active' and log the action.

    Raises:
        HTTPException 404 — user not found.
        HTTPException 400 — user is already active or deleted.
    """
    user: User | None = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    if user.status == "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already active",
        )
    if user.status == "deleted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot activate a deleted user",
        )

    previous_status = user.status
    user.status = "active"

    log_admin_action(
        db=db,
        admin_id=admin_id,
        action="activate_user",
        entity_type="user",
        entity_id=user_id,
        details={"email": user.email, "previous_status": previous_status},
    )

    db.commit()


def get_platform_stats(db: Session) -> dict:
    """
    Compute and return platform-wide statistics:

    - Total users broken down by role.
    - Total jobs broken down by status.
    - Total payment volume (sum of all payment amounts).
    - Count of open disputes.
    """
    # Users by role
    user_role_counts = (
        db.query(User.role, func.count(User.id))
        .group_by(User.role)
        .all()
    )
    users_by_role: dict[str, int] = {role: count for role, count in user_role_counts}

    # Jobs by status
    job_status_counts = (
        db.query(Job.status, func.count(Job.id))
        .group_by(Job.status)
        .all()
    )
    jobs_by_status: dict[str, int] = {
        job_status: count for job_status, count in job_status_counts
    }

    # Total payment volume
    total_volume_result = db.query(func.sum(Payment.amount)).scalar()
    total_payment_volume: float = (
        float(total_volume_result) if total_volume_result is not None else 0.0
    )

    # Open disputes count
    open_disputes_count: int = (
        db.query(func.count(Dispute.id))
        .filter(Dispute.status.in_(["open", "investigating"]))
        .scalar()
        or 0
    )

    return {
        "users_by_role": users_by_role,
        "jobs_by_status": jobs_by_status,
        "total_payment_volume": total_payment_volume,
        "open_disputes_count": open_disputes_count,
    }
