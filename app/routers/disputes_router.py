
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.schemas.dispute_schema import DisputeCreate, DisputeResolve
from app.services import dispute_service
from app.utils.jwt_handler import get_current_user, require_role

router = APIRouter(prefix="/disputes", tags=["Disputes"])


def _serialize_dispute(dispute) -> dict:
    """Return a JSON-serialisable dict for a Dispute ORM instance."""
    return {
        "id": str(dispute.id),
        "contract_id": str(dispute.contract_id),
        "opened_by": str(dispute.opened_by),
        "reason": dispute.reason,
        "status": dispute.status,
        "resolution": dispute.resolution,
        "resolved_by": str(dispute.resolved_by) if dispute.resolved_by else None,
        "created_at": dispute.created_at.isoformat(),
    }


@router.post(
    "",
    response_model=dict,
    status_code=201,
    summary="Open a dispute for a contract",
)
def open_dispute(
    data: DisputeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Open a dispute for the given contract.

    Accessible by any authenticated user who is a student or researcher on the
    contract.  The contract must not already be completed, cancelled, or disputed.
    """
    dispute = dispute_service.open_dispute(
        db=db,
        user_id=current_user.id,
        data=data,
    )
    return {"status": "success", "data": _serialize_dispute(dispute)}


@router.get(
    "/mine",
    response_model=dict,
    summary="List own disputes",
)
def get_my_disputes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Return all disputes opened by the authenticated user."""
    disputes = dispute_service.get_user_disputes(db=db, user_id=current_user.id)
    return {
        "status": "success",
        "data": {
            "items": [_serialize_dispute(d) for d in disputes],
            "total": len(disputes),
        },
    }


@router.get(
    "",
    response_model=dict,
    summary="List all disputes (admin only)",
)
def list_all_disputes(
    dispute_status: str | None = Query(
        default=None,
        alias="status",
        description="Filter by dispute status (open|investigating|resolved|closed)",
    ),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Results per page"),
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> dict:
    """List all disputes on the platform, optionally filtered by status."""
    disputes, total = dispute_service.get_all_disputes(
        db=db,
        dispute_status=dispute_status,
        page=page,
        page_size=page_size,
    )
    return {
        "status": "success",
        "data": {
            "items": [_serialize_dispute(d) for d in disputes],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }


@router.get(
    "/{dispute_id}",
    response_model=dict,
    summary="Get a dispute by ID",
)
def get_dispute(
    dispute_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Retrieve a dispute.

    Accessible by participants on the underlying contract, or admins.
    """
    from fastapi import HTTPException, status as http_status  # noqa: PLC0415
    from app.models.contract import Contract  # noqa: PLC0415

    dispute = dispute_service.get_dispute(db, dispute_id)

    contract = db.query(Contract).filter(Contract.id == dispute.contract_id).first()
    is_participant = (
        contract is not None
        and current_user.id in (contract.student_id, contract.researcher_id)
    )
    if not is_participant and current_user.role != "admin":
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Access denied. You are not a participant in this contract.",
        )

    return {"status": "success", "data": _serialize_dispute(dispute)}


@router.post(
    "/{dispute_id}/investigate",
    response_model=dict,
    summary="Mark a dispute as investigating (admin only)",
)
def set_investigating(
    dispute_id: uuid.UUID,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> dict:
    """Set a dispute's status to 'investigating'."""
    dispute = dispute_service.set_investigating(
        db=db,
        dispute_id=dispute_id,
        admin_id=current_user.id,
    )
    return {"status": "success", "data": _serialize_dispute(dispute)}


@router.post(
    "/{dispute_id}/resolve",
    response_model=dict,
    summary="Resolve a dispute (admin only)",
)
def resolve_dispute(
    dispute_id: uuid.UUID,
    data: DisputeResolve,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> dict:
    """
    Resolve a dispute, specifying the resolution text and outcome.

    Outcome options:
    - ``refund_student``     — refund escrowed payment to the student.
    - ``release_researcher`` — release escrowed payment to the researcher.
    - ``split``              — split the payment 50/50 between both parties.
    """
    dispute = dispute_service.resolve_dispute(
        db=db,
        dispute_id=dispute_id,
        admin_id=current_user.id,
        data=data,
    )
    return {"status": "success", "data": _serialize_dispute(dispute)}
