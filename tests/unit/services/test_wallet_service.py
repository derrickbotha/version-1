"""
Unit tests for payment_service wallet functions.
Tests are synchronous and use the db fixture directly.
"""
import uuid
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.contract import Contract
from app.models.job import Job
from app.models.payment import Payment, Wallet, WalletTransaction
from app.models.user import User, ResearcherProfile, StudentProfile
from app.schemas.payment_schema import EscrowDepositRequest
from app.services import payment_service


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(db: Session, role: str = "student") -> User:
    user = User(
        id=uuid.uuid4(),
        email=f"{uuid.uuid4().hex[:8]}@test.com",
        password_hash="hashed",
        first_name="Test",
        last_name="User",
        role=role,
        status="active",
    )
    db.add(user)
    db.flush()
    return user


def _make_job(db: Session, student_id: uuid.UUID) -> Job:
    job = Job(
        id=uuid.uuid4(),
        student_id=student_id,
        title="Test Job",
        description="A test job description for unit tests",
        subject="Computer Science",
        academic_level="Masters",
        proposed_price=Decimal("200.00"),
        status="accepted",
        deadline=None,
    )
    db.add(job)
    db.flush()
    return job


def _make_contract(
    db: Session,
    student_id: uuid.UUID,
    researcher_id: uuid.UUID,
    job_id: uuid.UUID,
    status: str = "accepted",
    price: Decimal = Decimal("200.00"),
) -> Contract:
    contract = Contract(
        id=uuid.uuid4(),
        job_id=job_id,
        student_id=student_id,
        researcher_id=researcher_id,
        agreed_price=price,
        status=status,
    )
    db.add(contract)
    db.flush()
    return contract


def _make_researcher_profile(db: Session, user_id: uuid.UUID) -> ResearcherProfile:
    profile = ResearcherProfile(
        user_id=user_id,
        bio="Test researcher bio",
        total_jobs_completed=0,
        rating=0,
    )
    db.add(profile)
    db.flush()
    return profile


def _fund_wallet(db: Session, user_id: uuid.UUID, amount: Decimal) -> Wallet:
    wallet = Wallet(user_id=user_id, balance=amount)
    db.add(wallet)
    db.flush()
    return wallet


# ---------------------------------------------------------------------------
# deposit_to_wallet
# ---------------------------------------------------------------------------

def test_deposit_creates_wallet_if_not_exists(db: Session) -> None:
    """deposit_to_wallet creates a wallet when none exists."""
    student = _make_user(db, "student")
    db.commit()

    wallet = payment_service.deposit_to_wallet(db, student.id, Decimal("50.00"))
    assert wallet is not None
    assert wallet.user_id == student.id


def test_deposit_increases_balance(db: Session) -> None:
    """deposit_to_wallet increases existing wallet balance."""
    student = _make_user(db, "student")
    _fund_wallet(db, student.id, Decimal("100.00"))
    db.commit()

    wallet = payment_service.deposit_to_wallet(db, student.id, Decimal("50.00"))
    assert Decimal(str(wallet.balance)) == Decimal("150.00")


def test_deposit_creates_wallet_transaction(db: Session) -> None:
    """deposit_to_wallet records a WalletTransaction of type 'deposit'."""
    student = _make_user(db, "student")
    db.commit()

    payment_service.deposit_to_wallet(db, student.id, Decimal("75.00"))

    txn = (
        db.query(WalletTransaction)
        .filter(
            WalletTransaction.wallet_id == student.id,
            WalletTransaction.transaction_type == "deposit",
        )
        .first()
    )
    assert txn is not None
    assert Decimal(str(txn.amount)) == Decimal("75.00")


# ---------------------------------------------------------------------------
# get_wallet
# ---------------------------------------------------------------------------

def test_get_wallet_returns_wallet(db: Session) -> None:
    """get_wallet returns the wallet for an existing user."""
    student = _make_user(db, "student")
    _fund_wallet(db, student.id, Decimal("200.00"))
    db.commit()

    wallet = payment_service.get_wallet(db, student.id)
    assert wallet.user_id == student.id


def test_get_wallet_raises_404_if_no_wallet(db: Session) -> None:
    """get_wallet raises HTTPException 404 if no wallet exists."""
    student = _make_user(db, "student")
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        payment_service.get_wallet(db, student.id)
    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# get_wallet_transactions
# ---------------------------------------------------------------------------

def test_get_wallet_transactions_returns_paginated_list(db: Session) -> None:
    """get_wallet_transactions returns a paginated list of transactions."""
    student = _make_user(db, "student")
    db.commit()

    # Create 2 deposits (stay under fraud limit of 3 rapid deposits)
    for amount in [Decimal("10.00"), Decimal("20.00")]:
        payment_service.deposit_to_wallet(db, student.id, amount)

    items, total = payment_service.get_wallet_transactions(db, student.id, page=1, page_size=10)
    assert total == 2
    assert len(items) == 2


def test_get_wallet_transactions_pagination_limits(db: Session) -> None:
    """get_wallet_transactions respects page_size."""
    student = _make_user(db, "student")
    db.commit()

    # Create 2 deposits using different users to avoid fraud limit
    for amount in [Decimal("10.00"), Decimal("20.00")]:
        payment_service.deposit_to_wallet(db, student.id, amount)

    items, total = payment_service.get_wallet_transactions(db, student.id, page=1, page_size=1)
    assert total == 2
    assert len(items) == 1


# ---------------------------------------------------------------------------
# create_escrow
# ---------------------------------------------------------------------------

def test_create_escrow_creates_payment_with_escrowed_status(db: Session) -> None:
    """create_escrow creates a Payment record with status=escrowed."""
    student = _make_user(db, "student")
    researcher = _make_user(db, "researcher")
    _fund_wallet(db, student.id, Decimal("500.00"))
    job = _make_job(db, student.id)
    contract = _make_contract(db, student.id, researcher.id, job.id, price=Decimal("200.00"))
    db.commit()

    data = EscrowDepositRequest(
        contract_id=contract.id,
        payment_provider="manual",
        provider_reference="test-ref-001",
    )
    payment = payment_service.create_escrow(db, contract.id, student.id, data)

    assert payment.status == "escrowed"
    assert payment.contract_id == contract.id


def test_create_escrow_reduces_wallet_balance(db: Session) -> None:
    """create_escrow deducts the agreed price from the student's wallet."""
    student = _make_user(db, "student")
    researcher = _make_user(db, "researcher")
    _fund_wallet(db, student.id, Decimal("500.00"))
    job = _make_job(db, student.id)
    contract = _make_contract(db, student.id, researcher.id, job.id, price=Decimal("200.00"))
    db.commit()

    data = EscrowDepositRequest(
        contract_id=contract.id,
        payment_provider="manual",
        provider_reference="test-ref-002",
    )
    payment_service.create_escrow(db, contract.id, student.id, data)

    wallet = db.query(Wallet).filter(Wallet.user_id == student.id).first()
    assert Decimal(str(wallet.balance)) == Decimal("300.00")


def test_create_escrow_raises_402_if_insufficient_balance(db: Session) -> None:
    """create_escrow raises 402 when wallet balance is too low."""
    student = _make_user(db, "student")
    researcher = _make_user(db, "researcher")
    _fund_wallet(db, student.id, Decimal("50.00"))
    job = _make_job(db, student.id)
    contract = _make_contract(db, student.id, researcher.id, job.id, price=Decimal("200.00"))
    db.commit()

    data = EscrowDepositRequest(
        contract_id=contract.id,
        payment_provider="manual",
        provider_reference="test-ref-003",
    )
    with pytest.raises(HTTPException) as exc_info:
        payment_service.create_escrow(db, contract.id, student.id, data)
    assert exc_info.value.status_code == 402


def test_create_escrow_raises_409_if_payment_already_exists(db: Session) -> None:
    """create_escrow raises 409 if a non-failed payment already exists."""
    student = _make_user(db, "student")
    researcher = _make_user(db, "researcher")
    _fund_wallet(db, student.id, Decimal("1000.00"))
    job = _make_job(db, student.id)
    contract = _make_contract(db, student.id, researcher.id, job.id, price=Decimal("200.00"))
    db.commit()

    data = EscrowDepositRequest(
        contract_id=contract.id,
        payment_provider="manual",
        provider_reference="test-ref-004",
    )
    payment_service.create_escrow(db, contract.id, student.id, data)

    # Fund again for second attempt
    wallet = db.query(Wallet).filter(Wallet.user_id == student.id).first()
    wallet.balance = Decimal("1000.00")
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        payment_service.create_escrow(db, contract.id, student.id, data)
    assert exc_info.value.status_code == 409


def test_create_escrow_raises_400_if_contract_not_accepted_status(db: Session) -> None:
    """create_escrow raises 400 when contract is not in accepted status."""
    student = _make_user(db, "student")
    researcher = _make_user(db, "researcher")
    _fund_wallet(db, student.id, Decimal("500.00"))
    job = _make_job(db, student.id)
    contract = _make_contract(db, student.id, researcher.id, job.id, status="in_progress", price=Decimal("200.00"))
    db.commit()

    data = EscrowDepositRequest(
        contract_id=contract.id,
        payment_provider="manual",
        provider_reference="test-ref-005",
    )
    with pytest.raises(HTTPException) as exc_info:
        payment_service.create_escrow(db, contract.id, student.id, data)
    assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# release_payment
# ---------------------------------------------------------------------------

def _setup_escrowed_contract(db: Session):
    """Helper: create student, researcher, contract, and escrowed payment."""
    student = _make_user(db, "student")
    researcher = _make_user(db, "researcher")
    _make_researcher_profile(db, researcher.id)
    _fund_wallet(db, student.id, Decimal("500.00"))
    job = _make_job(db, student.id)
    contract = _make_contract(db, student.id, researcher.id, job.id, price=Decimal("200.00"))
    db.commit()

    data = EscrowDepositRequest(
        contract_id=contract.id,
        payment_provider="manual",
        provider_reference="test-release-ref",
    )
    payment = payment_service.create_escrow(db, contract.id, student.id, data)

    # Advance contract to submitted
    contract.status = "submitted"
    db.commit()

    return student, researcher, contract, payment


def test_release_payment_sets_status_to_released(db: Session) -> None:
    """release_payment sets payment status to 'released'."""
    student, researcher, contract, payment = _setup_escrowed_contract(db)

    released = payment_service.release_payment(db, contract.id, student.id)
    assert released.status == "released"


def test_release_payment_credits_researcher_wallet(db: Session) -> None:
    """release_payment credits the researcher's wallet."""
    student, researcher, contract, payment = _setup_escrowed_contract(db)

    payment_service.release_payment(db, contract.id, student.id)

    researcher_wallet = db.query(Wallet).filter(Wallet.user_id == researcher.id).first()
    assert researcher_wallet is not None
    assert Decimal(str(researcher_wallet.balance)) == Decimal("200.00")


def test_release_payment_sets_contract_to_completed(db: Session) -> None:
    """release_payment transitions contract status to 'completed'."""
    student, researcher, contract, payment = _setup_escrowed_contract(db)

    payment_service.release_payment(db, contract.id, student.id)

    db.refresh(contract)
    assert contract.status == "completed"


# ---------------------------------------------------------------------------
# refund_payment
# ---------------------------------------------------------------------------

def _setup_escrowed_contract_for_refund(db: Session):
    """Helper: create escrowed contract ready for refund."""
    student = _make_user(db, "student")
    researcher = _make_user(db, "researcher")
    _fund_wallet(db, student.id, Decimal("500.00"))
    job = _make_job(db, student.id)
    contract = _make_contract(db, student.id, researcher.id, job.id, price=Decimal("200.00"))
    db.commit()

    data = EscrowDepositRequest(
        contract_id=contract.id,
        payment_provider="manual",
        provider_reference="test-refund-ref",
    )
    payment = payment_service.create_escrow(db, contract.id, student.id, data)
    return student, researcher, contract, payment


def test_refund_payment_sets_status_to_refunded(db: Session) -> None:
    """refund_payment sets payment status to 'refunded'."""
    student, researcher, contract, payment = _setup_escrowed_contract_for_refund(db)

    refunded = payment_service.refund_payment(db, contract.id, student.id, "student", "test reason for refund")
    assert refunded.status == "refunded"


def test_refund_payment_credits_student_wallet(db: Session) -> None:
    """refund_payment credits the student's wallet with the escrowed amount."""
    student, researcher, contract, payment = _setup_escrowed_contract_for_refund(db)
    # Student wallet after escrow: 500 - 200 = 300
    initial_wallet = db.query(Wallet).filter(Wallet.user_id == student.id).first()
    balance_before = Decimal(str(initial_wallet.balance))

    payment_service.refund_payment(db, contract.id, student.id, "student", "test reason for refund")

    db.refresh(initial_wallet)
    assert Decimal(str(initial_wallet.balance)) == balance_before + Decimal("200.00")


def test_refund_payment_sets_contract_to_cancelled(db: Session) -> None:
    """refund_payment transitions contract status to 'cancelled'."""
    student, researcher, contract, payment = _setup_escrowed_contract_for_refund(db)

    payment_service.refund_payment(db, contract.id, student.id, "student", "test reason for refund")

    db.refresh(contract)
    assert contract.status == "cancelled"
