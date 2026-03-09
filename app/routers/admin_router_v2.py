"""
Enhanced Admin API router (v2) — /api/v1/admin/*

Full platform management: users, professors, payouts, disputes,
transactions, config, analytics, and audit log.

All endpoints require role='admin' or 'super_admin'.
Endpoints marked [SUPER_ADMIN] require role='super_admin'.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.schemas.admin_schema import (
    AdminDisputeResolve,
    AssignProfessorRequest,
    ConfigUpdate,
    PayoutApproveRequest,
    PayoutRejectRequest,
    PlatformOverview,
    ProfessorApproveRequest,
    RoleAssignRequest,
    SuspendRequest,
)
from app.services import admin_service_v2 as svc
from app.utils.jwt_handler import get_current_user, require_role

router = APIRouter(prefix="/admin", tags=["Admin"])

_admin_dep = Depends(require_role("admin"))


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/dashboard", summary="Platform overview metrics")
def dashboard(
    db: Session = Depends(get_db),
    _current_user: User = _admin_dep,
) -> dict:
    """
    Real-time platform overview including user counts, job metrics,
    revenue summary, and quality indicators.
    """
    overview = svc.get_platform_overview(db)
    return {"status": "success", "data": overview}


# ─────────────────────────────────────────────────────────────────────────────
# User Management
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/users", summary="List all users")
def list_users(
    role: Optional[str] = Query(None),
    user_status: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    _current_user: User = _admin_dep,
) -> dict:
    """Paginated, filterable, searchable user list."""
    users, total = svc.get_users_list(db, role, user_status, search, page, page_size)
    items = [
        {
            "id": str(u.id), "email": u.email,
            "first_name": u.first_name, "last_name": u.last_name,
            "role": u.role, "status": u.status, "is_verified": u.is_verified,
            "created_at": u.created_at.isoformat(),
        }
        for u in users
    ]
    return {"status": "success", "data": {"items": items, "total": total, "page": page, "page_size": page_size}}


@router.get("/users/{user_id}", summary="Get user detail")
def get_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = _admin_dep,
) -> dict:
    """Full user detail including wallet balance and activity counts."""
    detail = svc.get_user_detail(db, user_id)
    user = detail["user"]
    return {
        "status": "success",
        "data": {
            "id": str(user.id), "email": user.email,
            "first_name": user.first_name, "last_name": user.last_name,
            "role": user.role, "status": user.status,
            "is_verified": user.is_verified, "phone": user.phone,
            "whatsapp_number": user.whatsapp_number,
            "failed_login_attempts": user.failed_login_attempts,
            "locked_until": user.locked_until.isoformat() if user.locked_until else None,
            "wallet_balance": detail["wallet_balance"],
            "total_jobs": detail["total_jobs"],
            "total_contracts": detail["total_contracts"],
            "created_at": user.created_at.isoformat(),
        },
    }


@router.post("/users/{user_id}/verify", summary="Verify user account")
def verify_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = _admin_dep,
) -> dict:
    """Mark a user account as verified (identity confirmed)."""
    user = svc.verify_user(db, user_id, current_user.id)
    return {"status": "success", "data": {"message": f"User {user.email} is now verified"}}


@router.post("/users/{user_id}/role", summary="Assign role to user [SUPER_ADMIN for admin roles]")
def assign_role(
    user_id: uuid.UUID,
    data: RoleAssignRequest,
    db: Session = Depends(get_db),
    current_user: User = _admin_dep,
) -> dict:
    """
    Assign a new role to a user.
    Assigning 'admin' or 'super_admin' requires the caller to be super_admin.
    """
    user = svc.assign_role(db, user_id, current_user.id, data.role, data.reason)
    return {
        "status": "success",
        "data": {"message": f"User {user.email} is now role={user.role}"},
    }


@router.patch("/users/{user_id}/suspend", summary="Suspend user")
def suspend_user(
    user_id: uuid.UUID,
    data: SuspendRequest,
    db: Session = Depends(get_db),
    current_user: User = _admin_dep,
) -> dict:
    """Suspend a user account with a required reason."""
    from app.services.admin_service import suspend_user as _suspend  # noqa
    _suspend(db, user_id, current_user.id)
    return {"status": "success", "data": {"message": f"User {user_id} suspended"}}


@router.patch("/users/{user_id}/unsuspend", summary="Re-activate suspended user")
def unsuspend_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = _admin_dep,
) -> dict:
    """Re-activate a suspended user account."""
    from app.services.admin_service import activate_user as _activate  # noqa
    _activate(db, user_id, current_user.id)
    return {"status": "success", "data": {"message": f"User {user_id} re-activated"}}


@router.post("/users/{user_id}/ban", summary="Permanently ban user [SUPER_ADMIN]")
def ban_user(
    user_id: uuid.UUID,
    data: SuspendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
) -> dict:
    """Permanently ban a user (soft delete). Only super_admin can do this."""
    svc.ban_user(db, user_id, current_user.id, data.reason)
    return {"status": "success", "data": {"message": f"User {user_id} has been banned"}}


# ─────────────────────────────────────────────────────────────────────────────
# Professor Management
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/professors", summary="List professor profiles")
def list_professors(
    status_filter: Optional[str] = Query(None, description="pending|approved|rejected|suspended"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    _current_user: User = _admin_dep,
) -> dict:
    """List professor profiles with approval status filter."""
    profs, total = svc.list_professors(db, status_filter, page, page_size)
    items = [
        {
            "id": str(p.id), "user_id": str(p.user_id),
            "user_email": p.user.email,
            "user_name": f"{p.user.first_name} {p.user.last_name}",
            "institution_name": p.institution.name if p.institution else None,
            "department": p.department, "academic_rank": p.academic_rank,
            "status": p.status, "total_reviews_completed": p.total_reviews_completed,
            "review_subjects": p.review_subjects,
            "created_at": p.created_at.isoformat(),
        }
        for p in profs
    ]
    return {"status": "success", "data": {"items": items, "total": total, "page": page, "page_size": page_size}}


@router.post("/professors/{professor_id}/action", summary="Approve or reject professor")
def action_professor(
    professor_id: uuid.UUID,
    data: ProfessorApproveRequest,
    db: Session = Depends(get_db),
    current_user: User = _admin_dep,
) -> dict:
    """
    Approve or reject a pending professor profile.
    Optionally override the default review fee for this professor.
    """
    prof = svc.action_professor(db, professor_id, current_user.id, data)
    return {
        "status": "success",
        "data": {"professor_id": str(prof.id), "status": prof.status},
    }


# ─────────────────────────────────────────────────────────────────────────────
# Dispute Management
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/disputes", summary="List all disputes")
def list_disputes(
    status_filter: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    _current_user: User = _admin_dep,
) -> dict:
    disputes, total = svc.list_all_disputes(db, status_filter, page, page_size)
    items = [
        {
            "id": str(d.id), "contract_id": str(d.contract_id),
            "job_title": d.contract.job.title if d.contract and d.contract.job else "—",
            "opened_by_email": d.opener.email if d.opener else "unknown",
            "reason": d.reason, "status": d.status,
            "created_at": d.created_at.isoformat(),
        }
        for d in disputes
    ]
    return {"status": "success", "data": {"items": items, "total": total, "page": page, "page_size": page_size}}


@router.post("/disputes/{dispute_id}/assign-professor", summary="Assign professor to dispute")
def assign_professor(
    dispute_id: uuid.UUID,
    data: AssignProfessorRequest,
    db: Session = Depends(get_db),
    current_user: User = _admin_dep,
) -> dict:
    """
    Assign an approved professor to arbitrate a dispute.
    Creates a high-priority (SLA=72h) queue item for the professor.
    """
    item = svc.assign_professor_to_dispute(db, dispute_id, current_user.id, data)
    return {
        "status": "success",
        "data": {
            "queue_item_id": str(item.id),
            "professor_id": str(item.professor_id),
            "due_at": item.due_at.isoformat() if item.due_at else None,
        },
    }


@router.post("/disputes/{dispute_id}/resolve", summary="Admin resolves dispute financially")
def resolve_dispute(
    dispute_id: uuid.UUID,
    data: AdminDisputeResolve,
    db: Session = Depends(get_db),
    current_user: User = _admin_dep,
) -> dict:
    """
    Admin executes the financial outcome of a dispute.
    Usually called after a professor ruling has been submitted.
    Can also be used to resolve without professor involvement.
    """
    dispute = svc.admin_resolve_dispute(db, dispute_id, current_user.id, data)
    return {
        "status": "success",
        "data": {"dispute_id": str(dispute.id), "status": dispute.status},
    }


# ─────────────────────────────────────────────────────────────────────────────
# Payout Management
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/payouts", summary="List all payout requests")
def list_payouts(
    status_filter: Optional[str] = Query(None, description="pending|processing|completed|failed"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    _current_user: User = _admin_dep,
) -> dict:
    payouts, total = svc.list_payouts(db, status_filter, page, page_size)
    items = [
        {
            "id": str(p.id), "writer_id": str(p.writer_id),
            "amount": float(p.amount), "currency": p.currency,
            "status": p.status, "provider": p.provider,
            "created_at": p.created_at.isoformat(),
        }
        for p in payouts
    ]
    return {"status": "success", "data": {"items": items, "total": total, "page": page, "page_size": page_size}}


@router.post("/payouts/{payout_id}/approve", summary="Approve payout")
def approve_payout(
    payout_id: uuid.UUID,
    data: PayoutApproveRequest,
    db: Session = Depends(get_db),
    current_user: User = _admin_dep,
) -> dict:
    """Approve a pending payout — moves it to 'processing' for disbursement."""
    payout = svc.approve_payout(db, payout_id, current_user.id, data)
    return {
        "status": "success",
        "data": {"payout_id": str(payout.id), "status": payout.status},
    }


@router.post("/payouts/{payout_id}/reject", summary="Reject and refund payout")
def reject_payout(
    payout_id: uuid.UUID,
    data: PayoutRejectRequest,
    db: Session = Depends(get_db),
    current_user: User = _admin_dep,
) -> dict:
    """Reject a payout and return funds to the writer's wallet."""
    payout = svc.reject_payout(db, payout_id, current_user.id, data)
    return {
        "status": "success",
        "data": {"payout_id": str(payout.id), "status": payout.status},
    }


# ─────────────────────────────────────────────────────────────────────────────
# Transactions
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/transactions", summary="Platform transaction ledger")
def list_transactions(
    tx_type: Optional[str] = Query(None, description="deposit|escrow_lock|release|refund|payout"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _current_user: User = _admin_dep,
) -> dict:
    txns, total, total_volume = svc.list_transactions(db, tx_type, page, page_size)
    items = [
        {
            "id": str(t.id), "wallet_id": str(t.wallet_id),
            "transaction_type": t.transaction_type,
            "amount": float(t.amount),
            "reference_id": str(t.reference_id) if t.reference_id else None,
            "notes": t.notes,
            "created_at": t.created_at.isoformat(),
        }
        for t in txns
    ]
    return {
        "status": "success",
        "data": {
            "items": items, "total": total,
            "total_deposit_volume": total_volume,
            "page": page, "page_size": page_size,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# Platform Config
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/config", summary="Get platform configuration")
def get_config(
    db: Session = Depends(get_db),
    _current_user: User = _admin_dep,
) -> dict:
    """List all platform configuration key/value pairs."""
    configs = svc.get_config(db)
    return {
        "status": "success",
        "data": [
            {
                "key": c.key, "value": c.value,
                "description": c.description,
                "updated_at": c.updated_at.isoformat(),
            }
            for c in configs
        ],
    }


@router.patch("/config/{key}", summary="Update a config value")
def set_config(
    key: str,
    data: ConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = _admin_dep,
) -> dict:
    """Update or create a platform configuration value."""
    cfg = svc.set_config(db, key, current_user.id, data)
    return {
        "status": "success",
        "data": {"key": cfg.key, "value": cfg.value},
    }


@router.post("/config/seed", summary="Seed default config values")
def seed_config(
    db: Session = Depends(get_db),
    _current_user: User = _admin_dep,
) -> dict:
    """Idempotently insert default configuration values."""
    svc.seed_default_config(db)
    return {"status": "success", "data": {"message": "Default config seeded"}}


# ─────────────────────────────────────────────────────────────────────────────
# Audit Log
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/audit-log", summary="Full audit trail")
def get_audit_log(
    admin_filter: Optional[uuid.UUID] = Query(None, description="Filter by admin user ID"),
    entity_type: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _current_user: User = _admin_dep,
) -> dict:
    """Full audit trail with optional filters by admin, entity, or action."""
    logs, total = svc.get_audit_logs(db, admin_filter, entity_type, action, page, page_size)
    items = [
        {
            "id": str(log.id),
            "admin_id": str(log.admin_id) if log.admin_id else None,
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": str(log.entity_id) if log.entity_id else None,
            "details": log.details,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]
    return {"status": "success", "data": {"items": items, "total": total, "page": page, "page_size": page_size}}
