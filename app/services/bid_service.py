
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.bid import Bid, BidCounter
from app.models.contract import Contract
from app.models.message import Conversation
from app.models.payment import Wallet
from app.schemas.bid_schema import BidCounterOffer, BidCreate
from app.services.job_service import get_job_by_id, transition_job_status
from app.utils.security import sanitize_input

_ACTIVE_BID_STATUSES = ("pending", "countered")


def place_bid(
    db: Session,
    job_id: uuid.UUID,
    researcher_id: uuid.UUID,
    data: BidCreate,
) -> Bid:
    """
    Place a bid on a job.

    Rules:
    - Job must exist and have status 'open' or 'negotiation'.
    - The researcher must not already have an active (pending/countered) bid on this job.
    - Bid is created with status='pending'.
    - If the job was 'open', it transitions to 'negotiation'.

    Raises:
        HTTPException 404 — job not found or deleted.
        HTTPException 400 — job is not accepting bids or researcher already bid.
    """
    job = get_job_by_id(db, job_id)

    if job.status not in ("open", "negotiation"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot place a bid on a job with status '{job.status}'. "
                "Job must be 'open' or 'negotiation'."
            ),
        )

    existing_bid: Bid | None = (
        db.query(Bid)
        .filter(
            Bid.job_id == job_id,
            Bid.researcher_id == researcher_id,
            Bid.status.in_(_ACTIVE_BID_STATUSES),
        )
        .first()
    )
    if existing_bid is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have an active bid on this job",
        )

    bid = Bid(
        id=uuid.uuid4(),
        job_id=job_id,
        researcher_id=researcher_id,
        proposed_price=data.proposed_price,
        message=sanitize_input(data.message),
        status="pending",
    )
    db.add(bid)

    # Transition job from 'open' to 'negotiation' on first bid
    if job.status == "open":
        job.status = "negotiation"

    db.commit()
    db.refresh(bid)
    return bid


def get_job_bids(db: Session, job_id: uuid.UUID) -> list[Bid]:
    """Return all bids for the given job."""
    return db.query(Bid).filter(Bid.job_id == job_id).all()


def accept_bid(
    db: Session,
    bid_id: uuid.UUID,
    student_id: uuid.UUID,
) -> Contract:
    """
    Accept a bid, creating a contract and rejecting all competing bids.

    Steps:
    1. Verify the bid exists and is in 'pending' or 'countered' status.
    2. Verify the student owns the related job.
    3. Set the accepted bid's status to 'accepted'.
    4. Reject all other non-withdrawn bids for the same job.
    5. Create a Contract with agreed_price from the bid.
    6. Create a Conversation for this job between student and researcher.
    7. Ensure the researcher has a Wallet (create one if not).
    8. Transition the job to 'accepted'.

    Raises:
        HTTPException 404 — bid not found.
        HTTPException 400 — bid is not in an acceptable status.
        HTTPException 403 — student does not own the job.
    """
    bid: Bid | None = db.query(Bid).filter(Bid.id == bid_id).first()
    if bid is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bid {bid_id} not found",
        )

    if bid.status not in ("pending", "countered"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot accept a bid with status '{bid.status}'. "
                "Bid must be 'pending' or 'countered'."
            ),
        )

    job = get_job_by_id(db, bid.job_id)

    if job.student_id != student_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to accept bids on this job",
        )

    # Capture the original status before mutation to decide agreed_price
    original_status = bid.status

    # Accept this bid
    bid.status = "accepted"

    # Reject all other active bids for the same job
    other_bids: list[Bid] = (
        db.query(Bid)
        .filter(
            Bid.job_id == bid.job_id,
            Bid.id != bid_id,
            Bid.status.in_(list(_ACTIVE_BID_STATUSES)),
        )
        .all()
    )
    for other in other_bids:
        if other.status not in ("withdrawn", "rejected", "accepted"):
            other.status = "rejected"

    # Determine agreed price: use latest counter price if bid was countered
    agreed_price = bid.proposed_price
    if original_status == "countered" and bid.counters:
        latest_counter = max(bid.counters, key=lambda c: c.created_at)
        agreed_price = latest_counter.new_price

    # Create contract
    contract = Contract(
        id=uuid.uuid4(),
        job_id=job.id,
        student_id=student_id,
        researcher_id=bid.researcher_id,
        agreed_price=agreed_price,
        deadline=job.deadline,
        status="accepted",
    )
    db.add(contract)

    # Create conversation between student and researcher for this job
    existing_conversation: Conversation | None = (
        db.query(Conversation)
        .filter(
            Conversation.job_id == job.id,
            Conversation.researcher_id == bid.researcher_id,
        )
        .first()
    )
    if existing_conversation is None:
        conversation = Conversation(
            id=uuid.uuid4(),
            job_id=job.id,
            student_id=student_id,
            researcher_id=bid.researcher_id,
        )
        db.add(conversation)

    # Ensure researcher wallet exists
    researcher_wallet: Wallet | None = (
        db.query(Wallet).filter(Wallet.user_id == bid.researcher_id).first()
    )
    if researcher_wallet is None:
        wallet = Wallet(user_id=bid.researcher_id, balance=0)
        db.add(wallet)

    # Transition job to accepted
    job.status = "accepted"

    db.commit()
    db.refresh(contract)
    return contract


def reject_bid(
    db: Session,
    bid_id: uuid.UUID,
    student_id: uuid.UUID,
) -> Bid:
    """
    Reject a bid.

    Raises:
        HTTPException 404 — bid not found.
        HTTPException 403 — student does not own the related job.
        HTTPException 400 — bid is not in a rejectable status.
    """
    bid: Bid | None = db.query(Bid).filter(Bid.id == bid_id).first()
    if bid is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bid {bid_id} not found",
        )

    job = get_job_by_id(db, bid.job_id)

    if job.student_id != student_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to reject bids on this job",
        )

    if bid.status not in ("pending", "countered"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot reject a bid with status '{bid.status}'. "
                "Bid must be 'pending' or 'countered'."
            ),
        )

    bid.status = "rejected"
    db.commit()
    db.refresh(bid)
    return bid


def counter_bid(
    db: Session,
    bid_id: uuid.UUID,
    student_id: uuid.UUID,
    data: BidCounterOffer,
) -> BidCounter:
    """
    Submit a counter-offer on a bid.

    - Verifies the student owns the related job.
    - Creates a BidCounter record.
    - Sets the bid status to 'countered'.

    Raises:
        HTTPException 404 — bid not found.
        HTTPException 403 — student does not own the related job.
        HTTPException 400 — bid is not in a counterable status.
    """
    bid: Bid | None = db.query(Bid).filter(Bid.id == bid_id).first()
    if bid is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bid {bid_id} not found",
        )

    job = get_job_by_id(db, bid.job_id)

    if job.student_id != student_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to counter bids on this job",
        )

    if bid.status not in ("pending", "countered"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot counter a bid with status '{bid.status}'. "
                "Bid must be 'pending' or 'countered'."
            ),
        )

    counter = BidCounter(
        id=uuid.uuid4(),
        bid_id=bid_id,
        counter_by=student_id,
        new_price=data.new_price,
        message=sanitize_input(data.message),
    )
    db.add(counter)

    bid.status = "countered"
    db.commit()
    db.refresh(counter)
    return counter


def withdraw_bid(
    db: Session,
    bid_id: uuid.UUID,
    researcher_id: uuid.UUID,
) -> Bid:
    """
    Allow a researcher to withdraw their own bid.

    Raises:
        HTTPException 404 — bid not found.
        HTTPException 403 — caller is not the bid owner.
        HTTPException 400 — bid is not in a withdrawable status.
    """
    bid: Bid | None = db.query(Bid).filter(Bid.id == bid_id).first()
    if bid is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bid {bid_id} not found",
        )

    if bid.researcher_id != researcher_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to withdraw this bid",
        )

    if bid.status not in ("pending", "countered"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot withdraw a bid with status '{bid.status}'. "
                "Bid must be 'pending' or 'countered'."
            ),
        )

    bid.status = "withdrawn"
    db.commit()
    db.refresh(bid)
    return bid


def get_researcher_bids(db: Session, researcher_id: uuid.UUID) -> list[Bid]:
    """Return all bids placed by the given researcher."""
    return (
        db.query(Bid)
        .filter(Bid.researcher_id == researcher_id)
        .order_by(Bid.created_at.desc())
        .all()
    )
