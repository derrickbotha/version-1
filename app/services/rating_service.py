
import uuid

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.contract import Contract, Rating
from app.models.user import ResearcherProfile
from app.schemas.rating_schema import RatingCreate
from app.utils.security import sanitize_input


def create_rating(
    db: Session,
    student_id: uuid.UUID,
    data: RatingCreate,
) -> Rating:
    """
    Submit a rating for a completed contract.

    Preconditions:
    - Contract must exist and belong to *student_id*.
    - Contract status must be 'completed'.
    - No rating must already exist for this contract.

    Side-effects:
    - Creates a Rating record.
    - Recalculates and updates the researcher's average rating on their profile.

    Raises:
        HTTPException 404 — contract not found.
        HTTPException 403 — student does not own the contract.
        HTTPException 400 — contract not completed, or rating already submitted.
    """
    contract: Contract | None = (
        db.query(Contract).filter(Contract.id == data.contract_id).first()
    )
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract {data.contract_id} not found",
        )

    if contract.student_id != student_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this contract",
        )

    if contract.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot rate a contract with status '{contract.status}'. "
                "Contract must be 'completed'."
            ),
        )

    existing: Rating | None = (
        db.query(Rating).filter(Rating.contract_id == data.contract_id).first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A rating already exists for this contract",
        )

    review_text: str | None = None
    if data.review:
        review_text = sanitize_input(data.review)

    rating = Rating(
        contract_id=data.contract_id,
        student_id=student_id,
        researcher_id=contract.researcher_id,
        rating=data.rating,
        review=review_text,
    )
    db.add(rating)
    db.flush()  # ensure rating is persisted before calculating average

    # Recalculate researcher's average rating across all their ratings
    avg_result = (
        db.query(func.avg(Rating.rating))
        .filter(Rating.researcher_id == contract.researcher_id)
        .scalar()
    )
    new_avg: float = float(avg_result) if avg_result is not None else float(data.rating)

    researcher_profile: ResearcherProfile | None = (
        db.query(ResearcherProfile)
        .filter(ResearcherProfile.user_id == contract.researcher_id)
        .first()
    )
    if researcher_profile is not None:
        researcher_profile.rating = round(new_avg, 2)

    db.commit()
    db.refresh(rating)
    return rating


def get_researcher_ratings(
    db: Session,
    researcher_id: uuid.UUID,
    page: int,
    page_size: int,
) -> tuple[list[Rating], int]:
    """
    Return a paginated list of ratings for *researcher_id* and the total count.
    """
    base_query = (
        db.query(Rating)
        .filter(Rating.researcher_id == researcher_id)
        .order_by(Rating.created_at.desc())
    )
    total: int = base_query.count()
    offset = (page - 1) * page_size
    items: list[Rating] = base_query.offset(offset).limit(page_size).all()
    return items, total


def get_rating_by_contract(
    db: Session,
    contract_id: uuid.UUID,
) -> Rating | None:
    """Return the Rating for *contract_id*, or None if no rating exists yet."""
    return db.query(Rating).filter(Rating.contract_id == contract_id).first()
