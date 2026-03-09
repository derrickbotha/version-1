
import json
import logging
import uuid
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.contract import Contract
from app.models.payment import IdempotencyKey, Payment, PaymentMethod, Wallet, WalletTransaction, WriterPayout
from app.models.user import ResearcherProfile
from app.schemas.payment_schema import EscrowDepositRequest, PayoutRequestSchema

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Wallet helpers
# ---------------------------------------------------------------------------

def _get_or_create_wallet(db: Session, user_id: uuid.UUID) -> Wallet:
    """Return the wallet for *user_id*, creating one with zero balance if absent."""
    wallet: Wallet | None = db.query(Wallet).filter(Wallet.user_id == user_id).first()
    if wallet is None:
        wallet = Wallet(user_id=user_id, balance=Decimal("0.00"))
        db.add(wallet)
        db.flush()
    return wallet


def _create_wallet_transaction(
    db: Session,
    wallet_id: uuid.UUID,
    amount: Decimal,
    transaction_type: str,
    reference_id: uuid.UUID | None = None,
    notes: str | None = None,
) -> WalletTransaction:
    tx = WalletTransaction(
        wallet_id=wallet_id,
        amount=amount,
        transaction_type=transaction_type,
        reference_id=reference_id,
        notes=notes,
    )
    db.add(tx)
    return tx


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Idempotency helpers (spec §12)
# ---------------------------------------------------------------------------

def check_idempotency(
    db: Session,
    key: str,
    user_id: uuid.UUID,
    endpoint: str,
) -> dict | None:
    """Return cached response dict if key already processed, else None."""
    record = db.query(IdempotencyKey).filter(
        IdempotencyKey.key == key,
        IdempotencyKey.user_id == user_id,
    ).first()
    if record:
        return json.loads(record.response_body)
    return None


def store_idempotency(
    db: Session,
    key: str,
    user_id: uuid.UUID,
    endpoint: str,
    response: dict,
) -> None:
    record = IdempotencyKey(
        key=key,
        user_id=user_id,
        endpoint=endpoint,
        response_body=json.dumps(response, default=str),
    )
    db.add(record)
    db.commit()


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------

def deposit_to_wallet(
    db: Session,
    user_id: uuid.UUID,
    amount: Decimal,
) -> Wallet:
    """
    Credit *amount* to the wallet owned by *user_id*, creating the wallet
    record if it does not yet exist.  Records a WalletTransaction of type
    'deposit'.
    """
    # Fraud check (spec §11)
    from app.services import fraud_service  # noqa: PLC0415
    flagged, reason = fraud_service.check_deposit(user_id, float(amount))
    if flagged:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=reason)

    wallet = _get_or_create_wallet(db, user_id)
    wallet.balance = Decimal(str(wallet.balance)) + amount
    _create_wallet_transaction(
        db,
        wallet_id=user_id,
        amount=amount,
        transaction_type="deposit",
        notes="Wallet deposit",
    )

    # Double-entry ledger (spec §6 — deposit example)
    from app.services.ledger_service import post_double_entry  # noqa: PLC0415
    post_double_entry(
        db,
        transaction_ref=f"deposit:{user_id}:{amount}",
        debit_type="PAYMENT_PROCESSOR",
        credit_type="USER_WALLET",
        amount=amount,
        credit_owner=user_id,
        description="Wallet deposit",
    )

    db.commit()
    db.refresh(wallet)
    logger.info("Wallet deposit: user=%s amount=%s", user_id, amount)
    return wallet


def get_wallet(db: Session, user_id: uuid.UUID) -> Wallet:
    """
    Return the wallet for *user_id*.

    Raises:
        HTTPException 404 — if the wallet does not exist.
    """
    wallet: Wallet | None = db.query(Wallet).filter(Wallet.user_id == user_id).first()
    if wallet is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found. Please make a deposit first.",
        )
    return wallet


def get_wallet_transactions(
    db: Session,
    user_id: uuid.UUID,
    page: int,
    page_size: int,
) -> tuple[list[WalletTransaction], int]:
    """
    Return a paginated list of WalletTransaction records for *user_id* and
    the total count, ordered newest-first.
    """
    base_query = (
        db.query(WalletTransaction)
        .filter(WalletTransaction.wallet_id == user_id)
        .order_by(WalletTransaction.created_at.desc())
    )
    total: int = base_query.count()
    items: list[WalletTransaction] = base_query.offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def create_escrow(
    db: Session,
    contract_id: uuid.UUID,
    student_id: uuid.UUID,
    data: EscrowDepositRequest,
) -> Payment:
    """
    Lock contract funds in escrow.

    Preconditions:
    - Contract must exist and belong to *student_id*.
    - Contract status must be 'accepted'.
    - No non-failed payment may already exist for this contract.
    - Student wallet balance must cover the agreed price.

    Raises:
        HTTPException 404 — contract not found.
        HTTPException 403 — contract does not belong to student.
        HTTPException 400 — contract not in 'accepted' status.
        HTTPException 409 — payment already exists for this contract.
        HTTPException 402 — insufficient wallet balance.
    """
    contract: Contract | None = db.query(Contract).filter(Contract.id == contract_id).first()
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract {contract_id} not found",
        )

    if contract.student_id != student_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to escrow funds for this contract",
        )

    if contract.status != "accepted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot escrow payment for a contract with status '{contract.status}'. "
                "Contract must be in 'accepted' status."
            ),
        )

    existing: Payment | None = (
        db.query(Payment)
        .filter(
            Payment.contract_id == contract_id,
            Payment.status != "failed",
        )
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A payment already exists for contract {contract_id} with status '{existing.status}'",
        )

    amount = Decimal(str(contract.agreed_price))

    # Debit student wallet
    wallet = _get_or_create_wallet(db, student_id)
    balance = Decimal(str(wallet.balance))
    if balance < amount:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                f"Insufficient wallet balance. Required: {amount}, available: {balance}. "
                "Please top up your wallet first."
            ),
        )

    wallet.balance = balance - amount
    _create_wallet_transaction(
        db,
        wallet_id=student_id,
        amount=amount,
        transaction_type="escrow_lock",
        reference_id=contract_id,
        notes=f"Escrow lock for contract {contract_id}",
    )

    payment = Payment(
        contract_id=contract_id,
        student_id=student_id,
        researcher_id=contract.researcher_id,
        amount=amount,
        status="escrowed",
        payment_provider=data.payment_provider,
        provider_reference=data.provider_reference,
    )
    db.add(payment)

    # Double-entry ledger: user wallet → escrow (spec §6 — order payment example)
    from app.services.ledger_service import post_double_entry  # noqa: PLC0415
    post_double_entry(
        db,
        transaction_ref=f"escrow:{contract_id}",
        debit_type="USER_WALLET",
        credit_type="ESCROW_ACCOUNT",
        amount=amount,
        debit_owner=student_id,
        description=f"Escrow lock for contract {contract_id}",
    )

    db.commit()
    db.refresh(payment)

    logger.info(
        "Escrow created: payment=%s contract=%s student=%s amount=%s",
        payment.id,
        contract_id,
        student_id,
        amount,
    )
    return payment


def release_payment(
    db: Session,
    contract_id: uuid.UUID,
    student_id: uuid.UUID,
) -> Payment:
    """
    Release escrowed funds to the researcher.

    Preconditions:
    - Contract must belong to *student_id*.
    - Contract status must be 'submitted' or 'completed'.
    - Payment status must be 'escrowed'.

    Post-conditions:
    - Payment set to 'released'.
    - Researcher wallet credited.
    - Contract set to 'completed'.
    - ResearcherProfile.total_jobs_completed incremented.

    Raises:
        HTTPException 404 — contract or payment not found.
        HTTPException 403 — contract does not belong to student.
        HTTPException 400 — contract or payment in wrong status.
    """
    contract: Contract | None = db.query(Contract).filter(Contract.id == contract_id).first()
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract {contract_id} not found",
        )

    if contract.student_id != student_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to release payment for this contract",
        )

    if contract.status not in ("submitted", "completed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot release payment for a contract with status '{contract.status}'. "
                "Contract must be in 'submitted' or 'completed' status."
            ),
        )

    payment: Payment | None = (
        db.query(Payment)
        .filter(
            Payment.contract_id == contract_id,
            Payment.status == "escrowed",
        )
        .first()
    )
    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No escrowed payment found for this contract",
        )

    amount = Decimal(str(payment.amount))

    payment.status = "released"

    # Credit researcher wallet
    researcher_wallet = _get_or_create_wallet(db, contract.researcher_id)
    researcher_wallet.balance = Decimal(str(researcher_wallet.balance)) + amount

    _create_wallet_transaction(
        db,
        wallet_id=student_id,
        amount=amount,
        transaction_type="release",
        reference_id=contract_id,
        notes=f"Payment release for contract {contract_id}",
    )
    _create_wallet_transaction(
        db,
        wallet_id=contract.researcher_id,
        amount=amount,
        transaction_type="payout",
        reference_id=contract_id,
        notes=f"Payout for contract {contract_id}",
    )

    # Double-entry ledger: escrow → writer wallet (spec §6 — escrow release example)
    from app.services.ledger_service import post_double_entry  # noqa: PLC0415
    post_double_entry(
        db,
        transaction_ref=f"release:{contract_id}",
        debit_type="ESCROW_ACCOUNT",
        credit_type="WRITER_WALLET",
        amount=amount,
        credit_owner=contract.researcher_id,
        description=f"Payment release for contract {contract_id}",
    )

    # Complete the contract
    contract.status = "completed"

    # Increment researcher jobs completed
    researcher_profile: ResearcherProfile | None = (
        db.query(ResearcherProfile)
        .filter(ResearcherProfile.user_id == contract.researcher_id)
        .first()
    )
    if researcher_profile is not None:
        researcher_profile.total_jobs_completed += 1

    db.commit()
    db.refresh(payment)

    logger.info(
        "Payment released: payment=%s contract=%s researcher=%s amount=%s",
        payment.id,
        contract_id,
        contract.researcher_id,
        amount,
    )
    return payment


def refund_payment(
    db: Session,
    contract_id: uuid.UUID,
    requester_id: uuid.UUID,
    requester_role: str,
    reason: str,
) -> Payment:
    """
    Refund escrowed funds back to the student.

    Preconditions:
    - Requester must be the student on the contract or an admin.
    - Payment status must be 'escrowed'.

    Post-conditions:
    - Payment set to 'refunded'.
    - Student wallet credited.
    - Contract set to 'cancelled'.

    Raises:
        HTTPException 404 — contract or payment not found.
        HTTPException 403 — requester is not the student or admin.
        HTTPException 400 — payment not in 'escrowed' status.
    """
    contract: Contract | None = db.query(Contract).filter(Contract.id == contract_id).first()
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract {contract_id} not found",
        )

    if requester_role != "admin" and contract.student_id != requester_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to request a refund for this contract",
        )

    payment: Payment | None = (
        db.query(Payment)
        .filter(
            Payment.contract_id == contract_id,
            Payment.status == "escrowed",
        )
        .first()
    )
    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No escrowed payment found for this contract",
        )

    amount = Decimal(str(payment.amount))

    payment.status = "refunded"

    # Credit student wallet
    student_wallet = _get_or_create_wallet(db, contract.student_id)
    student_wallet.balance = Decimal(str(student_wallet.balance)) + amount

    _create_wallet_transaction(
        db,
        wallet_id=contract.student_id,
        amount=amount,
        transaction_type="refund",
        reference_id=contract_id,
        notes=f"Refund for contract {contract_id}: {reason}",
    )

    contract.status = "cancelled"

    db.commit()
    db.refresh(payment)

    logger.info(
        "Payment refunded: payment=%s contract=%s student=%s amount=%s reason=%s",
        payment.id,
        contract_id,
        contract.student_id,
        amount,
        reason,
    )
    return payment


# ---------------------------------------------------------------------------
# Payment methods (spec §4.7)
# ---------------------------------------------------------------------------

def get_payment_methods(db: Session, user_id: uuid.UUID) -> list[PaymentMethod]:
    return (
        db.query(PaymentMethod)
        .filter(PaymentMethod.user_id == user_id)
        .order_by(PaymentMethod.created_at.desc())
        .all()
    )


def delete_payment_method(db: Session, pm_id: uuid.UUID, user_id: uuid.UUID) -> None:
    pm = db.query(PaymentMethod).filter(
        PaymentMethod.id == pm_id, PaymentMethod.user_id == user_id
    ).first()
    if pm is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment method not found")
    db.delete(pm)
    db.commit()


def set_default_payment_method(db: Session, pm_id: uuid.UUID, user_id: uuid.UUID) -> PaymentMethod:
    # Clear existing default
    db.query(PaymentMethod).filter(PaymentMethod.user_id == user_id).update({"is_default": False})
    pm = db.query(PaymentMethod).filter(
        PaymentMethod.id == pm_id, PaymentMethod.user_id == user_id
    ).first()
    if pm is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment method not found")
    pm.is_default = True
    db.commit()
    db.refresh(pm)
    return pm


# ---------------------------------------------------------------------------
# Writer payout (spec §4.10, §10)
# ---------------------------------------------------------------------------

def request_payout(
    db: Session,
    writer_id: uuid.UUID,
    data: PayoutRequestSchema,
) -> WriterPayout:
    """
    Writer requests a payout from their wallet balance.

    Preconditions:
    - Wallet balance >= requested amount.

    Post-conditions:
    - Wallet debited.
    - WriterPayout created with status 'pending'.
    - Ledger: WRITER_WALLET → PAYOUT_CLEARING.
    """
    wallet = _get_or_create_wallet(db, writer_id)
    balance = Decimal(str(wallet.balance))
    amount = data.amount

    if balance < amount:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Insufficient balance. Available: ${balance}, requested: ${amount}",
        )

    wallet.balance = balance - amount
    _create_wallet_transaction(
        db,
        wallet_id=writer_id,
        amount=amount,
        transaction_type="payout",
        notes=f"Payout request via {data.provider}",
    )

    payout = WriterPayout(
        writer_id=writer_id,
        amount=float(amount),
        currency="USD",
        status="pending",
        provider=data.provider,
    )
    db.add(payout)

    # Ledger: writer wallet → payout clearing
    from app.services.ledger_service import post_double_entry  # noqa: PLC0415
    post_double_entry(
        db,
        transaction_ref=f"payout:{writer_id}:{amount}",
        debit_type="WRITER_WALLET",
        credit_type="PAYOUT_CLEARING",
        amount=amount,
        debit_owner=writer_id,
        description=f"Payout request ${amount} via {data.provider}",
    )

    db.commit()
    db.refresh(payout)
    logger.info("Payout requested: writer=%s amount=%s provider=%s", writer_id, amount, data.provider)
    return payout


def get_payouts(
    db: Session,
    writer_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[WriterPayout], int]:
    q = (
        db.query(WriterPayout)
        .filter(WriterPayout.writer_id == writer_id)
        .order_by(WriterPayout.created_at.desc())
    )
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def get_payment_by_contract(
    db: Session,
    contract_id: uuid.UUID,
    requester_id: uuid.UUID,
    requester_role: str,
) -> Payment:
    """
    Return the payment record for *contract_id*.

    Access is restricted to the student, researcher on the contract, or
    an admin.

    Raises:
        HTTPException 404 — contract or payment not found.
        HTTPException 403 — requester is not a participant or admin.
    """
    contract: Contract | None = db.query(Contract).filter(Contract.id == contract_id).first()
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract {contract_id} not found",
        )

    is_participant = (
        contract.student_id == requester_id
        or contract.researcher_id == requester_id
    )
    if requester_role != "admin" and not is_participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view payment details for this contract",
        )

    payment: Payment | None = (
        db.query(Payment)
        .filter(Payment.contract_id == contract_id)
        .order_by(Payment.created_at.desc())
        .first()
    )
    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No payment found for contract {contract_id}",
        )
    return payment
