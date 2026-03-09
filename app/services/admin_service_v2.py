"""
Enhanced admin service (v2) — comprehensive platform management.

Adds to the original admin_service:
  - Full user management (verify, role assignment, ban, unsuspend)
  - Professor approval workflow
  - Payout approval/rejection
  - Dispute assignment to professors
  - Dispute financial resolution
  - Platform config CRUD
  - Rich analytics (overview, revenue, user growth, job metrics)
  - Audit log retrieval
  - Transaction listing with aggregates
  - Job/contract management (flag, feature, remove)
"""

import datetime as _dt
import uuid
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, joinedload

from app.models.audit_log import AuditLog
from app.models.contract import Contract, Dispute
from app.models.job import Job
from app.models.payment import Payment, Wallet, WalletTransaction, WriterPayout
from app.models.professor import (
    DisputeRuling,
    PlatformConfig,
    ProfessorProfile,
    QualityReview,
    ReviewQueueItem,
)
from app.models.user import User
from app.schemas.admin_schema import (
    AdminDisputeResolve,
    AssignProfessorRequest,
    ConfigUpdate,
    PayoutApproveRequest,
    PayoutRejectRequest,
    ProfessorApproveRequest,
    SuspendRequest,
)
from app.services.admin_service import log_admin_action


# ─────────────────────────────────────────────────────────────────────────────
# User Management
# ─────────────────────────────────────────────────────────────────────────────

def get_user_detail(db: Session, user_id: uuid.UUID) -> dict:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    wallet = db.execute(
        select(Wallet).where(Wallet.user_id == user_id)
    ).scalar_one_or_none()

    job_count = db.execute(
        select(func.count()).where(Job.student_id == user_id)
    ).scalar() or 0

    contract_count = db.execute(
        select(func.count()).where(
            (Contract.student_id == user_id) | (Contract.researcher_id == user_id)
        )
    ).scalar() or 0

    return {
        "user": user,
        "wallet_balance": float(wallet.balance) if wallet else None,
        "total_jobs": job_count,
        "total_contracts": contract_count,
    }


def verify_user(db: Session, user_id: uuid.UUID, admin_id: uuid.UUID) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    user.is_verified = True
    log_admin_action(db, admin_id, "verify_user", "user", user_id,
                     {"email": user.email})
    db.commit()
    db.refresh(user)
    return user


def assign_role(
    db: Session, user_id: uuid.UUID, admin_id: uuid.UUID, new_role: str, reason: Optional[str]
) -> User:
    allowed_roles = {"student", "researcher", "professor", "admin", "super_admin"}
    if new_role not in allowed_roles:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Invalid role. Must be one of: {allowed_roles}",
        )

    # Only super_admin can assign admin/super_admin roles
    admin = db.get(User, admin_id)
    if new_role in ("admin", "super_admin") and admin.role != "super_admin":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Only super_admin can assign admin or super_admin roles",
        )

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    old_role = user.role
    user.role = new_role
    log_admin_action(
        db, admin_id, "assign_role", "user", user_id,
        {"email": user.email, "old_role": old_role, "new_role": new_role, "reason": reason},
    )
    db.commit()
    db.refresh(user)
    return user


def ban_user(db: Session, user_id: uuid.UUID, admin_id: uuid.UUID, reason: str) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    user.status = "deleted"  # permanent ban = soft delete
    log_admin_action(db, admin_id, "ban_user", "user", user_id,
                     {"email": user.email, "reason": reason})
    db.commit()
    db.refresh(user)
    return user


def get_users_list(
    db: Session,
    role: Optional[str] = None,
    user_status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[User], int]:
    q = select(User).order_by(User.created_at.desc())
    if role:
        q = q.where(User.role == role)
    if user_status:
        q = q.where(User.status == user_status)
    if search:
        like = f"%{search}%"
        q = q.where(
            (User.email.ilike(like))
            | (User.first_name.ilike(like))
            | (User.last_name.ilike(like))
        )
    total = db.execute(select(func.count()).select_from(q.subquery())).scalar() or 0
    items = list(db.execute(q.offset((page - 1) * page_size).limit(page_size)).scalars())
    return items, total


# ─────────────────────────────────────────────────────────────────────────────
# Professor Approval
# ─────────────────────────────────────────────────────────────────────────────

def list_professors(
    db: Session,
    status_filter: Optional[str] = None,
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[ProfessorProfile], int]:
    q = (
        select(ProfessorProfile)
        .options(joinedload(ProfessorProfile.user), joinedload(ProfessorProfile.institution))
        .order_by(ProfessorProfile.created_at.desc())
    )
    if status_filter:
        q = q.where(ProfessorProfile.status == status_filter)
    total = db.execute(select(func.count()).select_from(q.subquery())).scalar() or 0
    items = list(db.execute(q.offset((page - 1) * page_size).limit(page_size)).scalars())
    return items, total


def action_professor(
    db: Session,
    professor_id: uuid.UUID,
    admin_id: uuid.UUID,
    data: ProfessorApproveRequest,
) -> ProfessorProfile:
    prof = db.get(ProfessorProfile, professor_id)
    if not prof:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Professor profile not found")

    if data.action == "approve":
        prof.status = "approved"
        prof.approved_by = admin_id
        prof.approved_at = _dt.datetime.now(_dt.timezone.utc)
        if data.review_fee_override is not None:
            prof.review_fee_per_job = data.review_fee_override
        action_label = "approve_professor"
    elif data.action == "reject":
        prof.status = "rejected"
        action_label = "reject_professor"
    else:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "action must be 'approve' or 'reject'"
        )

    log_admin_action(
        db, admin_id, action_label, "professor_profile", professor_id,
        {"reason": data.reason},
    )
    db.commit()
    db.refresh(prof)
    return prof


# ─────────────────────────────────────────────────────────────────────────────
# Payout Management
# ─────────────────────────────────────────────────────────────────────────────

def list_payouts(
    db: Session,
    status_filter: Optional[str] = None,
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[WriterPayout], int]:
    q = select(WriterPayout).order_by(WriterPayout.created_at.desc())
    if status_filter:
        q = q.where(WriterPayout.status == status_filter)
    total = db.execute(select(func.count()).select_from(q.subquery())).scalar() or 0
    items = list(db.execute(q.offset((page - 1) * page_size).limit(page_size)).scalars())
    return items, total


def approve_payout(
    db: Session, payout_id: uuid.UUID, admin_id: uuid.UUID, data: PayoutApproveRequest
) -> WriterPayout:
    payout = db.get(WriterPayout, payout_id)
    if not payout:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payout not found")
    if payout.status != "pending":
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Payout is already in status: {payout.status}"
        )

    payout.status = "processing"
    if data.notes:
        payout.notes = data.notes
    log_admin_action(
        db, admin_id, "approve_payout", "writer_payout", payout_id,
        {"amount": float(payout.amount), "currency": payout.currency},
    )
    db.commit()
    db.refresh(payout)
    return payout


def reject_payout(
    db: Session, payout_id: uuid.UUID, admin_id: uuid.UUID, data: PayoutRejectRequest
) -> WriterPayout:
    payout = db.get(WriterPayout, payout_id)
    if not payout:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payout not found")
    if payout.status != "pending":
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Payout cannot be rejected in status: {payout.status}"
        )

    payout.status = "failed"
    payout.notes = data.reason

    # Refund the amount back to the writer's wallet
    wallet = db.execute(
        select(Wallet).where(Wallet.user_id == payout.writer_id)
    ).scalar_one_or_none()
    if wallet:
        wallet.balance = float(wallet.balance) + float(payout.amount)
        refund_tx = WalletTransaction(
            wallet_id=payout.writer_id,
            amount=payout.amount,
            transaction_type="refund",
            reference_id=payout_id,
            notes=f"Payout rejected: {data.reason}",
        )
        db.add(refund_tx)

    log_admin_action(
        db, admin_id, "reject_payout", "writer_payout", payout_id,
        {"reason": data.reason, "amount": float(payout.amount)},
    )
    db.commit()
    db.refresh(payout)
    return payout


# ─────────────────────────────────────────────────────────────────────────────
# Dispute Management
# ─────────────────────────────────────────────────────────────────────────────

def assign_professor_to_dispute(
    db: Session,
    dispute_id: uuid.UUID,
    admin_id: uuid.UUID,
    data: AssignProfessorRequest,
) -> ReviewQueueItem:
    dispute = db.get(Dispute, dispute_id)
    if not dispute:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dispute not found")

    prof = db.get(ProfessorProfile, data.professor_id)
    if not prof or prof.status != "approved":
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Approved professor not found"
        )

    # Check no existing arbitration queue item
    existing = db.execute(
        select(ReviewQueueItem).where(
            ReviewQueueItem.contract_id == dispute.contract_id,
            ReviewQueueItem.queue_type == "dispute_arbitration",
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "A professor has already been assigned to this dispute"
        )

    item = ReviewQueueItem(
        contract_id=dispute.contract_id,
        professor_id=prof.id,
        queue_type="dispute_arbitration",
        status="assigned",
        priority=1,  # disputes are highest priority
        sla_hours=72,
        due_at=_dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(hours=72),
        assigned_at=_dt.datetime.now(_dt.timezone.utc),
        notes=data.notes,
    )
    db.add(item)
    dispute.status = "investigating"

    log_admin_action(
        db, admin_id, "assign_professor_dispute", "dispute", dispute_id,
        {"professor_id": str(data.professor_id)},
    )
    db.commit()
    db.refresh(item)
    return item


def admin_resolve_dispute(
    db: Session,
    dispute_id: uuid.UUID,
    admin_id: uuid.UUID,
    data: AdminDisputeResolve,
) -> Dispute:
    dispute = db.get(Dispute, dispute_id)
    if not dispute:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dispute not found")
    if dispute.status == "resolved":
        raise HTTPException(status.HTTP_409_CONFLICT, "Dispute already resolved")

    contract = db.get(Contract, dispute.contract_id)

    # Execute financial action
    if data.financial_action == "full_release":
        contract.status = "completed"
    elif data.financial_action == "full_refund":
        contract.status = "cancelled"
    elif data.financial_action == "partial_release":
        if data.release_percentage is None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "release_percentage required for partial_release"
            )
        contract.status = "completed"
    else:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "financial_action must be: full_release | partial_release | full_refund"
        )

    dispute.status = "resolved"
    dispute.resolution = data.resolution
    dispute.resolved_by = admin_id

    log_admin_action(
        db, admin_id, "resolve_dispute", "dispute", dispute_id,
        {
            "financial_action": data.financial_action,
            "release_percentage": data.release_percentage,
            "resolution": data.resolution,
        },
    )
    db.commit()
    db.refresh(dispute)
    return dispute


def list_all_disputes(
    db: Session,
    status_filter: Optional[str] = None,
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[Dispute], int]:
    q = (
        select(Dispute)
        .options(joinedload(Dispute.contract), joinedload(Dispute.opener))
        .order_by(Dispute.created_at.desc())
    )
    if status_filter:
        q = q.where(Dispute.status == status_filter)
    total = db.execute(select(func.count()).select_from(q.subquery())).scalar() or 0
    items = list(db.execute(q.offset((page - 1) * page_size).limit(page_size)).scalars())
    return items, total


# ─────────────────────────────────────────────────────────────────────────────
# Transaction Ledger View
# ─────────────────────────────────────────────────────────────────────────────

def list_transactions(
    db: Session,
    tx_type: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[WalletTransaction], int, float]:
    q = select(WalletTransaction).order_by(WalletTransaction.created_at.desc())
    if tx_type:
        q = q.where(WalletTransaction.transaction_type == tx_type)
    total = db.execute(select(func.count()).select_from(q.subquery())).scalar() or 0
    total_volume = db.execute(
        select(func.sum(WalletTransaction.amount))
        .where(WalletTransaction.transaction_type == "deposit")
    ).scalar() or 0.0
    items = list(db.execute(q.offset((page - 1) * page_size).limit(page_size)).scalars())
    return items, total, float(total_volume)


# ─────────────────────────────────────────────────────────────────────────────
# Platform Config
# ─────────────────────────────────────────────────────────────────────────────

def get_config(db: Session) -> list[PlatformConfig]:
    return list(db.execute(select(PlatformConfig).order_by(PlatformConfig.key)).scalars())


def get_config_value(db: Session, key: str) -> str:
    cfg = db.get(PlatformConfig, key)
    return cfg.value if cfg else ""


def set_config(
    db: Session, key: str, admin_id: uuid.UUID, data: ConfigUpdate
) -> PlatformConfig:
    cfg = db.get(PlatformConfig, key)
    if cfg:
        cfg.value = data.value
        if data.description:
            cfg.description = data.description
        cfg.updated_by = admin_id
    else:
        cfg = PlatformConfig(
            key=key,
            value=data.value,
            description=data.description,
            updated_by=admin_id,
        )
        db.add(cfg)

    log_admin_action(db, admin_id, "update_config", "platform_config", None,
                     {"key": key, "value": data.value})
    db.commit()
    db.refresh(cfg)
    return cfg


def seed_default_config(db: Session) -> None:
    """Insert default config values if they don't exist (idempotent)."""
    defaults = {
        "platform_fee_pct": ("15", "% of released payment taken as platform fee"),
        "professor_review_fee_usd": ("5.00", "Base USD paid to professor per completed review"),
        "max_revision_rounds": ("3", "Max revision rounds before contract auto-disputes"),
        "quality_review_required": ("false", "Require professor review before payment release"),
        "dispute_sla_hours": ("72", "Hours professor has to submit dispute ruling"),
        "review_sla_hours": ("48", "Hours professor has to complete a quality review"),
        "payout_min_usd": ("10", "Minimum payout amount in USD"),
        "fraud_deposit_limit_per_2min": ("3", "Max deposits per 2 minutes"),
        "fraud_failure_limit_per_10min": ("5", "Max payment failures per 10 minutes"),
        "fraud_kyc_threshold_usd": ("2000", "USD threshold above which KYC is flagged"),
    }
    for key, (val, desc) in defaults.items():
        if not db.get(PlatformConfig, key):
            db.add(PlatformConfig(key=key, value=val, description=desc))
    db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Analytics
# ─────────────────────────────────────────────────────────────────────────────

def get_platform_overview(db: Session) -> dict:
    now = _dt.datetime.now(_dt.timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # User counts
    role_counts = dict(
        db.execute(select(User.role, func.count(User.id)).group_by(User.role)).all()
    )
    total_users = sum(role_counts.values())
    active_users = db.execute(
        select(func.count()).where(User.status == "active")
    ).scalar() or 0
    new_this_month = db.execute(
        select(func.count()).where(User.created_at >= month_start)
    ).scalar() or 0

    # Job counts
    job_status_counts = dict(
        db.execute(select(Job.status, func.count(Job.id)).group_by(Job.status)).all()
    )
    total_jobs = sum(job_status_counts.values())
    completed_jobs = job_status_counts.get("completed", 0)
    disputed_jobs = job_status_counts.get("disputed", 0)
    open_jobs = job_status_counts.get("open", 0)

    # Revenue
    total_volume = db.execute(
        select(func.sum(WalletTransaction.amount)).where(
            WalletTransaction.transaction_type == "deposit"
        )
    ).scalar() or 0.0

    pending_payouts = db.execute(
        select(func.sum(WriterPayout.amount)).where(WriterPayout.status == "pending")
    ).scalar() or 0.0

    platform_fee_pct = float(get_config_value(db, "platform_fee_pct") or "15")
    estimated_platform_revenue = float(total_volume) * (platform_fee_pct / 100)

    # Quality
    avg_review_score = db.execute(
        select(func.avg(QualityReview.score)).where(QualityReview.score.isnot(None))
    ).scalar() or 0.0

    completion_rate = (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0.0

    return {
        "total_users": total_users,
        "active_users": active_users,
        "students": role_counts.get("student", 0),
        "researchers": role_counts.get("researcher", 0),
        "professors": role_counts.get("professor", 0),
        "new_users_this_month": new_this_month,
        "total_jobs": total_jobs,
        "open_jobs": open_jobs,
        "completed_jobs": completed_jobs,
        "disputed_jobs": disputed_jobs,
        "total_volume_usd": float(total_volume),
        "platform_revenue_usd": estimated_platform_revenue,
        "pending_payouts_usd": float(pending_payouts),
        "avg_completion_rate": round(completion_rate, 1),
        "avg_review_score": round(float(avg_review_score), 1),
        "avg_dispute_resolution_hours": 0.0,  # placeholder for time-series calculation
    }


def get_audit_logs(
    db: Session,
    admin_id_filter: Optional[uuid.UUID] = None,
    entity_type: Optional[str] = None,
    action: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[AuditLog], int]:
    q = (
        select(AuditLog)
        .options(joinedload(AuditLog.admin))
        .order_by(AuditLog.created_at.desc())
    )
    if admin_id_filter:
        q = q.where(AuditLog.admin_id == admin_id_filter)
    if entity_type:
        q = q.where(AuditLog.entity_type == entity_type)
    if action:
        q = q.where(AuditLog.action.ilike(f"%{action}%"))
    total = db.execute(select(func.count()).select_from(q.subquery())).scalar() or 0
    items = list(db.execute(q.offset((page - 1) * page_size).limit(page_size)).scalars())
    return items, total
