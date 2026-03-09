
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.schemas.bid_schema import (
    BidCounterOffer,
    BidCounterResponse,
    BidCreate,
    BidListResponse,
    BidResponse,
)
from app.schemas.contract_schema import ContractResponse
from app.services import bid_service
from app.utils.jwt_handler import get_current_user, require_role

router = APIRouter(tags=["Bids"])


@router.post(
    "/jobs/{job_id}/bids",
    response_model=dict,
    status_code=201,
    summary="Place a bid on a job",
)
def place_bid(
    job_id: uuid.UUID,
    body: BidCreate,
    current_user: User = Depends(require_role("researcher")),
    db: Session = Depends(get_db),
) -> dict:
    """Place a bid on a job. Restricted to researchers."""
    bid = bid_service.place_bid(
        db=db,
        job_id=job_id,
        researcher_id=current_user.id,
        data=body,
    )
    return {
        "status": "success",
        "data": BidResponse.model_validate(bid).model_dump(),
    }


@router.get(
    "/jobs/{job_id}/bids",
    response_model=dict,
    summary="List bids for a job",
)
def list_job_bids(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    List all bids for a job.

    Access is restricted to the job's student owner or an admin.
    Researchers may only see their own bid via GET /bids/mine.
    """
    from app.services.job_service import get_job_by_id
    from fastapi import HTTPException, status

    job = get_job_by_id(db=db, job_id=job_id)

    if current_user.role not in ("admin",) and job.student_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only the job owner or an admin may view all bids.",
        )

    bids = bid_service.get_job_bids(db=db, job_id=job_id)
    response = BidListResponse(
        items=[BidResponse.model_validate(b) for b in bids],
        total=len(bids),
    )
    return {"status": "success", "data": response.model_dump()}


@router.post(
    "/bids/{bid_id}/accept",
    response_model=dict,
    summary="Accept a bid",
)
def accept_bid(
    bid_id: uuid.UUID,
    current_user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
) -> dict:
    """Accept a bid and create a contract. Restricted to the job's student owner."""
    contract = bid_service.accept_bid(
        db=db,
        bid_id=bid_id,
        student_id=current_user.id,
    )
    return {
        "status": "success",
        "data": ContractResponse.model_validate(contract).model_dump(),
    }


@router.post(
    "/bids/{bid_id}/reject",
    response_model=dict,
    summary="Reject a bid",
)
def reject_bid(
    bid_id: uuid.UUID,
    current_user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
) -> dict:
    """Reject a bid. Restricted to the job's student owner."""
    bid = bid_service.reject_bid(
        db=db,
        bid_id=bid_id,
        student_id=current_user.id,
    )
    return {
        "status": "success",
        "data": BidResponse.model_validate(bid).model_dump(),
    }


@router.post(
    "/bids/{bid_id}/counter",
    response_model=dict,
    summary="Counter a bid",
)
def counter_bid(
    bid_id: uuid.UUID,
    body: BidCounterOffer,
    current_user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
) -> dict:
    """Submit a counter-offer on a bid. Restricted to the job's student owner."""
    counter = bid_service.counter_bid(
        db=db,
        bid_id=bid_id,
        student_id=current_user.id,
        data=body,
    )
    return {
        "status": "success",
        "data": BidCounterResponse.model_validate(counter).model_dump(),
    }


@router.post(
    "/bids/{bid_id}/withdraw",
    response_model=dict,
    summary="Withdraw a bid",
)
def withdraw_bid(
    bid_id: uuid.UUID,
    current_user: User = Depends(require_role("researcher")),
    db: Session = Depends(get_db),
) -> dict:
    """Withdraw a bid. Restricted to the researcher who placed the bid."""
    bid = bid_service.withdraw_bid(
        db=db,
        bid_id=bid_id,
        researcher_id=current_user.id,
    )
    return {
        "status": "success",
        "data": BidResponse.model_validate(bid).model_dump(),
    }


@router.get(
    "/bids/mine",
    response_model=dict,
    summary="Get own bids (researcher)",
)
def get_my_bids(
    current_user: User = Depends(require_role("researcher")),
    db: Session = Depends(get_db),
) -> dict:
    """Return all bids placed by the authenticated researcher."""
    bids = bid_service.get_researcher_bids(db=db, researcher_id=current_user.id)
    response = BidListResponse(
        items=[BidResponse.model_validate(b) for b in bids],
        total=len(bids),
    )
    return {"status": "success", "data": response.model_dump()}
