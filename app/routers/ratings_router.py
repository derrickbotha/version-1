
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.schemas.rating_schema import RatingCreate, RatingResponse
from app.services import rating_service
from app.utils.jwt_handler import get_current_user, require_role

router = APIRouter(prefix="/ratings", tags=["Ratings"])


def _serialize_rating(rating) -> dict:
    """Return a JSON-serialisable dict for a Rating ORM instance."""
    return {
        "id": str(rating.id),
        "contract_id": str(rating.contract_id),
        "student_id": str(rating.student_id),
        "researcher_id": str(rating.researcher_id),
        "rating": rating.rating,
        "review": rating.review,
        "created_at": rating.created_at.isoformat(),
    }


@router.post(
    "",
    response_model=dict,
    status_code=201,
    summary="Submit a rating for a completed contract",
)
def create_rating(
    data: RatingCreate,
    current_user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
) -> dict:
    """
    Submit a star rating (1–5) and optional written review for a completed contract.

    Accessible by students only.  The contract must be completed and must not
    already have a rating.
    """
    rating = rating_service.create_rating(
        db=db,
        student_id=current_user.id,
        data=data,
    )
    return {"status": "success", "data": _serialize_rating(rating)}


@router.get(
    "/researcher/{researcher_id}",
    response_model=dict,
    summary="Get paginated ratings for a researcher",
)
def get_researcher_ratings(
    researcher_id: uuid.UUID,
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Results per page"),
    db: Session = Depends(get_db),
) -> dict:
    """
    List all ratings for a researcher.  This endpoint is publicly accessible —
    no authentication required.
    """
    ratings, total = rating_service.get_researcher_ratings(
        db=db,
        researcher_id=researcher_id,
        page=page,
        page_size=page_size,
    )
    return {
        "status": "success",
        "data": {
            "items": [_serialize_rating(r) for r in ratings],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }


@router.get(
    "/contract/{contract_id}",
    response_model=dict,
    summary="Get the rating for a specific contract",
)
def get_rating_by_contract(
    contract_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Retrieve the rating for a specific contract.

    Accessible by authenticated participants on the contract, or admins.
    Returns null data if no rating has been submitted yet.
    """
    from fastapi import HTTPException, status as http_status  # noqa: PLC0415
    from app.models.contract import Contract  # noqa: PLC0415

    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if contract is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Contract {contract_id} not found",
        )

    is_participant = current_user.id in (contract.student_id, contract.researcher_id)
    if not is_participant and current_user.role != "admin":
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Access denied. You are not a participant in this contract.",
        )

    rating = rating_service.get_rating_by_contract(db=db, contract_id=contract_id)
    return {
        "status": "success",
        "data": _serialize_rating(rating) if rating else None,
    }
