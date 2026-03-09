
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.contract import Contract
from app.models.payment import Payment


def get_contract(db: Session, contract_id: uuid.UUID) -> Contract:
    """
    Fetch a single contract by primary key.

    Raises:
        HTTPException 404 — if the contract does not exist.
    """
    contract: Contract | None = (
        db.query(Contract).filter(Contract.id == contract_id).first()
    )
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract {contract_id} not found",
        )
    return contract


def get_user_contracts(
    db: Session,
    user_id: uuid.UUID,
    role: str,
) -> list[Contract]:
    """
    Return all contracts for a user, filtered by their role.

    - role='student'    → filter by contract.student_id
    - role='researcher' → filter by contract.researcher_id
    - role='admin'      → return all contracts

    Returns an empty list for unrecognised roles.
    """
    query = db.query(Contract)

    if role == "student":
        query = query.filter(Contract.student_id == user_id)
    elif role == "researcher":
        query = query.filter(Contract.researcher_id == user_id)
    elif role == "admin":
        pass  # no filter — admins see everything
    else:
        return []

    return query.order_by(Contract.created_at.desc()).all()


def start_contract(
    db: Session,
    contract_id: uuid.UUID,
    researcher_id: uuid.UUID,
) -> Contract:
    """
    Transition a contract to 'in_progress'.

    Preconditions:
    - The contract must exist.
    - The caller must be the researcher on the contract.
    - At least one Payment for this contract must have status='escrowed'.
    - Contract must currently be in 'accepted' status.

    Raises:
        HTTPException 404 — contract not found.
        HTTPException 403 — researcher does not own this contract.
        HTTPException 402 — no escrowed payment found for this contract.
        HTTPException 400 — contract is not in 'accepted' status.
    """
    contract = get_contract(db, contract_id)

    if contract.researcher_id != researcher_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to start this contract",
        )

    if contract.status != "accepted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot start a contract with status '{contract.status}'. "
                "Contract must be in 'accepted' status."
            ),
        )

    escrowed_payment: Payment | None = (
        db.query(Payment)
        .filter(
            Payment.contract_id == contract_id,
            Payment.status == "escrowed",
        )
        .first()
    )
    if escrowed_payment is None:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                "Cannot start work: payment has not been escrowed. "
                "The student must complete payment before work can begin."
            ),
        )

    contract.status = "in_progress"
    contract.start_date = datetime.now(timezone.utc)
    db.commit()
    db.refresh(contract)
    return contract


def get_contract_with_details(
    db: Session,
    contract_id: uuid.UUID,
) -> dict:
    """
    Return a contract enriched with its related job details and payment status.

    Raises:
        HTTPException 404 — contract not found.
    """
    contract = get_contract(db, contract_id)

    # Collect all payment statuses for this contract
    payments: list[Payment] = (
        db.query(Payment)
        .filter(Payment.contract_id == contract_id)
        .all()
    )
    payment_statuses = [p.status for p in payments]
    has_escrowed = any(p.status == "escrowed" for p in payments)

    job = contract.job

    return {
        "id": str(contract.id),
        "job_id": str(contract.job_id),
        "student_id": str(contract.student_id),
        "researcher_id": str(contract.researcher_id),
        "agreed_price": float(contract.agreed_price),
        "start_date": contract.start_date.isoformat() if contract.start_date else None,
        "deadline": contract.deadline.isoformat() if contract.deadline else None,
        "status": contract.status,
        "created_at": contract.created_at.isoformat(),
        "payment_statuses": payment_statuses,
        "payment_escrowed": has_escrowed,
        "job": {
            "id": str(job.id),
            "title": job.title,
            "subject": job.subject,
            "academic_level": job.academic_level,
            "description": job.description,
            "proposed_price": float(job.proposed_price),
            "status": job.status,
            "deadline": job.deadline.isoformat() if job.deadline else None,
        } if job is not None else None,
    }
