
import uuid
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.contract import Contract, Dispute
from app.models.message import Notification
from app.models.payment import Payment, Wallet, WalletTransaction
from app.models.user import User
from app.schemas.dispute_schema import DisputeCreate, DisputeResolve
from app.utils.security import sanitize_input

# Contract statuses that cannot have a new dispute opened
_BLOCKED_STATUSES = {"completed", "cancelled", "disputed"}


def _create_notification(
    db: Session,
    user_id: uuid.UUID,
    title: str,
    message: str,
    notification_type: str,
) -> None:
    """Persist an in-app notification record for *user_id*."""
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
    )
    db.add(notification)


def _credit_wallet(
    db: Session,
    user_id: uuid.UUID,
    amount: Decimal,
    transaction_type: str,
    reference_id: uuid.UUID,
    notes: str,
) -> None:
    """Credit *amount* to *user_id*'s wallet and record a transaction."""
    wallet: Wallet | None = db.query(Wallet).filter(Wallet.user_id == user_id).first()
    if wallet is None:
        # Create wallet if missing (should not happen in normal flow)
        wallet = Wallet(user_id=user_id, balance=Decimal("0.00"))
        db.add(wallet)
        db.flush()

    wallet.balance = Decimal(str(wallet.balance)) + amount

    txn = WalletTransaction(
        wallet_id=user_id,
        amount=amount,
        transaction_type=transaction_type,
        reference_id=reference_id,
        notes=notes,
    )
    db.add(txn)


def open_dispute(
    db: Session,
    user_id: uuid.UUID,
    data: DisputeCreate,
) -> Dispute:
    """
    Open a dispute for *data.contract_id*.

    Preconditions:
    - Contract must exist.
    - Calling user must be the student or researcher on the contract.
    - Contract status must not be in {completed, cancelled, disputed}.
    - No open dispute must already exist for this contract.

    Side-effects:
    - Creates a Dispute with status='open'.
    - Transitions contract status to 'disputed'.
    - Notifies both parties and all admin users.

    Raises:
        HTTPException 404 — contract not found.
        HTTPException 403 — user is not a participant.
        HTTPException 400 — contract status does not allow a new dispute, or
                            an open dispute already exists.
    """
    contract: Contract | None = (
        db.query(Contract).filter(Contract.id == data.contract_id).first()
    )
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract {data.contract_id} not found",
        )

    is_student = contract.student_id == user_id
    is_researcher = contract.researcher_id == user_id
    if not is_student and not is_researcher:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant in this contract",
        )

    if contract.status in _BLOCKED_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot open a dispute for a contract with status "
                f"'{contract.status}'."
            ),
        )

    existing: Dispute | None = (
        db.query(Dispute)
        .filter(
            Dispute.contract_id == data.contract_id,
            Dispute.status.in_(["open", "investigating"]),
        )
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An open or investigating dispute already exists for this contract",
        )

    reason_text = sanitize_input(data.reason)

    dispute = Dispute(
        contract_id=data.contract_id,
        opened_by=user_id,
        reason=reason_text,
        status="open",
    )
    db.add(dispute)

    contract.status = "disputed"

    # Notify the other party
    other_party_id = contract.researcher_id if is_student else contract.student_id
    dispute_msg = (
        f"A dispute has been opened for contract {data.contract_id}. "
        f"Reason: {reason_text}"
    )
    _create_notification(
        db=db,
        user_id=other_party_id,
        title="Dispute opened",
        message=dispute_msg,
        notification_type="dispute_opened",
    )
    _create_notification(
        db=db,
        user_id=user_id,
        title="Your dispute has been submitted",
        message=f"Your dispute for contract {data.contract_id} is under review.",
        notification_type="dispute_opened",
    )

    # Notify all admins
    admins: list[User] = (
        db.query(User)
        .filter(User.role == "admin", User.status == "active")
        .all()
    )
    for admin in admins:
        _create_notification(
            db=db,
            user_id=admin.id,
            title="New dispute requires attention",
            message=dispute_msg,
            notification_type="dispute_opened",
        )

    db.commit()
    db.refresh(dispute)
    return dispute


def resolve_dispute(
    db: Session,
    dispute_id: uuid.UUID,
    admin_id: uuid.UUID,
    data: DisputeResolve,
) -> Dispute:
    """
    Resolve an open or investigating dispute.

    Role enforcement is handled by the router (admin required).

    Outcomes:
    - 'refund_student'     : mark payment refunded, credit student wallet.
    - 'release_researcher' : mark payment released, credit researcher wallet.
    - 'split'              : split payment 50/50 between both wallets.

    Side-effects:
    - Updates dispute status to 'resolved'.
    - Transitions contract to 'completed' (release/split) or 'cancelled' (refund).

    Raises:
        HTTPException 404 — dispute not found.
        HTTPException 400 — dispute is not in a resolvable state.
    """
    dispute = get_dispute(db, dispute_id)

    if dispute.status not in ("open", "investigating"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot resolve a dispute with status '{dispute.status}'. "
                "Dispute must be 'open' or 'investigating'."
            ),
        )

    resolution_text = sanitize_input(data.resolution)
    dispute.status = "resolved"
    dispute.resolution = resolution_text
    dispute.resolved_by = admin_id

    contract: Contract | None = (
        db.query(Contract).filter(Contract.id == dispute.contract_id).first()
    )

    # Find the escrowed payment for this contract
    payment: Payment | None = (
        db.query(Payment)
        .filter(
            Payment.contract_id == dispute.contract_id,
            Payment.status == "escrowed",
        )
        .first()
    )

    outcome = data.outcome

    if outcome == "refund_student":
        if payment is not None:
            payment.status = "refunded"
            amount = Decimal(str(payment.amount))
            _credit_wallet(
                db=db,
                user_id=payment.student_id,
                amount=amount,
                transaction_type="refund",
                reference_id=payment.id,
                notes=f"Dispute resolution refund for contract {dispute.contract_id}",
            )
        if contract is not None:
            contract.status = "cancelled"

    elif outcome == "release_researcher":
        if payment is not None:
            payment.status = "released"
            amount = Decimal(str(payment.amount))
            _credit_wallet(
                db=db,
                user_id=payment.researcher_id,
                amount=amount,
                transaction_type="release",
                reference_id=payment.id,
                notes=(
                    f"Dispute resolution payment release for contract "
                    f"{dispute.contract_id}"
                ),
            )
        if contract is not None:
            contract.status = "completed"

    elif outcome == "split":
        if payment is not None:
            payment.status = "released"
            total = Decimal(str(payment.amount))
            half = (total / Decimal("2")).quantize(Decimal("0.01"))
            remainder = total - half  # handle odd cents: researcher gets the extra

            _credit_wallet(
                db=db,
                user_id=payment.student_id,
                amount=half,
                transaction_type="refund",
                reference_id=payment.id,
                notes=(
                    f"Dispute split resolution (50%) for contract "
                    f"{dispute.contract_id}"
                ),
            )
            _credit_wallet(
                db=db,
                user_id=payment.researcher_id,
                amount=remainder,
                transaction_type="release",
                reference_id=payment.id,
                notes=(
                    f"Dispute split resolution (50%) for contract "
                    f"{dispute.contract_id}"
                ),
            )
        if contract is not None:
            contract.status = "completed"

    db.commit()
    db.refresh(dispute)
    return dispute


def get_dispute(db: Session, dispute_id: uuid.UUID) -> Dispute:
    """
    Fetch a single dispute by primary key.

    Raises:
        HTTPException 404 — if not found.
    """
    dispute: Dispute | None = (
        db.query(Dispute).filter(Dispute.id == dispute_id).first()
    )
    if dispute is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dispute {dispute_id} not found",
        )
    return dispute


def get_all_disputes(
    db: Session,
    dispute_status: str | None,
    page: int,
    page_size: int,
) -> tuple[list[Dispute], int]:
    """
    Return a paginated list of all disputes (admin view), optionally filtered
    by *dispute_status*.
    """
    query = db.query(Dispute).order_by(Dispute.created_at.desc())
    if dispute_status:
        query = query.filter(Dispute.status == dispute_status)
    total: int = query.count()
    offset = (page - 1) * page_size
    items: list[Dispute] = query.offset(offset).limit(page_size).all()
    return items, total


def get_user_disputes(db: Session, user_id: uuid.UUID) -> list[Dispute]:
    """Return all disputes where *user_id* is the opener."""
    return (
        db.query(Dispute)
        .filter(Dispute.opened_by == user_id)
        .order_by(Dispute.created_at.desc())
        .all()
    )


def set_investigating(
    db: Session,
    dispute_id: uuid.UUID,
    admin_id: uuid.UUID,
) -> Dispute:
    """
    Mark a dispute as 'investigating'.

    Admin role enforcement is handled by the router.

    Raises:
        HTTPException 404 — dispute not found.
        HTTPException 400 — dispute is not in 'open' status.
    """
    dispute = get_dispute(db, dispute_id)

    if dispute.status != "open":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot set 'investigating' on a dispute with status "
                f"'{dispute.status}'. Dispute must be 'open'."
            ),
        )

    dispute.status = "investigating"
    db.commit()
    db.refresh(dispute)
    return dispute
