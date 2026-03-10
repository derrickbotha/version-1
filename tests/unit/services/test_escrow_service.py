"""
Unit tests for escrow edge cases in payment_service.
"""
import uuid
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.contract import Contract
from app.models.job import Job
from app.models.payment import Payment, Wallet, WalletTransaction, LedgerEntry
from app.models.user import User, ResearcherProfile
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
        description="A test job for escrow unit tests that is reasonably long",
        subject="Mathematics",
        academic_level="Bachelors",
        proposed_price=Decimal("100.00"),
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
    price: Decimal = Decimal("100.00"),
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


def _fund_wallet(db: Session, user_id: uuid.UUID, amount: Decimal) -> Wallet:
    wallet = Wallet(user_id=user_id, balance=amount)
    db.add(wallet)
    db.flush()
    return wallet


def _make_researcher_profile(db: Session, user_id: uuid.UUID) -> ResearcherProfile:
    profile = ResearcherProfile(
        user_id=user_id,
        bio="Test researcher",
        total_jobs_completed=0,
        rating=0,
    )
    db.add(profile)
    db.flush()
    return profile


def _escrow_request(contract_id: uuid.UUID, ref: str = "test-ref") -> EscrowDepositRequest:
    return EscrowDepositRequest(
        contract_id=contract_id,
        payment_provider="manual",
        provider_reference=ref,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_double_escrow_on_same_contract_raises_409(db: Session) -> None:
    """Second escrow attempt on same contract raises 409."""
    student = _make_user(db, "student")
    researcher = _make_user(db, "researcher")
    _fund_wallet(db, student.id, Decimal("1000.00"))
    job = _make_job(db, student.id)
    contract = _make_contract(db, student.id, researcher.id, job.id)
    db.commit()

    payment_service.create_escrow(db, contract.id, student.id, _escrow_request(contract.id, "ref-1"))

    # Re-fund wallet for second attempt
    wallet = db.query(Wallet).filter(Wallet.user_id == student.id).first()
    wallet.balance = Decimal("1000.00")
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        payment_service.create_escrow(db, contract.id, student.id, _escrow_request(contract.id, "ref-2"))
    assert exc_info.value.status_code == 409


def test_escrow_with_zero_balance_raises_402(db: Session) -> None:
    """Escrow with zero wallet balance raises 402."""
    student = _make_user(db, "student")
    researcher = _make_user(db, "researcher")
    _fund_wallet(db, student.id, Decimal("0.00"))
    job = _make_job(db, student.id)
    contract = _make_contract(db, student.id, researcher.id, job.id, price=Decimal("100.00"))
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        payment_service.create_escrow(db, contract.id, student.id, _escrow_request(contract.id))
    assert exc_info.value.status_code == 402


def test_escrow_with_exact_balance_succeeds(db: Session) -> None:
    """Escrow with exactly the required amount succeeds and leaves zero balance."""
    student = _make_user(db, "student")
    researcher = _make_user(db, "researcher")
    _fund_wallet(db, student.id, Decimal("100.00"))
    job = _make_job(db, student.id)
    contract = _make_contract(db, student.id, researcher.id, job.id, price=Decimal("100.00"))
    db.commit()

    payment = payment_service.create_escrow(db, contract.id, student.id, _escrow_request(contract.id))
    assert payment.status == "escrowed"

    wallet = db.query(Wallet).filter(Wallet.user_id == student.id).first()
    assert Decimal(str(wallet.balance)) == Decimal("0.00")


def test_escrow_with_more_than_balance_fails(db: Session) -> None:
    """Escrow fails when price exceeds wallet balance by even $0.01."""
    student = _make_user(db, "student")
    researcher = _make_user(db, "researcher")
    _fund_wallet(db, student.id, Decimal("99.99"))
    job = _make_job(db, student.id)
    contract = _make_contract(db, student.id, researcher.id, job.id, price=Decimal("100.00"))
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        payment_service.create_escrow(db, contract.id, student.id, _escrow_request(contract.id))
    assert exc_info.value.status_code == 402


def test_escrow_on_wrong_contract_raises_403(db: Session) -> None:
    """A user who is not the student on the contract gets 403."""
    student = _make_user(db, "student")
    other_student = _make_user(db, "student")
    researcher = _make_user(db, "researcher")
    _fund_wallet(db, other_student.id, Decimal("1000.00"))
    job = _make_job(db, student.id)
    contract = _make_contract(db, student.id, researcher.id, job.id)
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        payment_service.create_escrow(
            db, contract.id, other_student.id, _escrow_request(contract.id)
        )
    assert exc_info.value.status_code == 403


def test_escrow_on_in_progress_contract_raises_400(db: Session) -> None:
    """Escrow on an in_progress contract raises 400."""
    student = _make_user(db, "student")
    researcher = _make_user(db, "researcher")
    _fund_wallet(db, student.id, Decimal("500.00"))
    job = _make_job(db, student.id)
    contract = _make_contract(db, student.id, researcher.id, job.id, status="in_progress")
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        payment_service.create_escrow(db, contract.id, student.id, _escrow_request(contract.id))
    assert exc_info.value.status_code == 400


def test_escrow_on_completed_contract_raises_400(db: Session) -> None:
    """Escrow on a completed contract raises 400."""
    student = _make_user(db, "student")
    researcher = _make_user(db, "researcher")
    _fund_wallet(db, student.id, Decimal("500.00"))
    job = _make_job(db, student.id)
    contract = _make_contract(db, student.id, researcher.id, job.id, status="completed")
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        payment_service.create_escrow(db, contract.id, student.id, _escrow_request(contract.id))
    assert exc_info.value.status_code == 400


def test_after_escrow_student_wallet_reduced_by_agreed_price(db: Session) -> None:
    """After escrow, student wallet balance is exactly reduced by agreed_price."""
    student = _make_user(db, "student")
    researcher = _make_user(db, "researcher")
    _fund_wallet(db, student.id, Decimal("300.00"))
    job = _make_job(db, student.id)
    contract = _make_contract(db, student.id, researcher.id, job.id, price=Decimal("150.00"))
    db.commit()

    payment_service.create_escrow(db, contract.id, student.id, _escrow_request(contract.id))

    wallet = db.query(Wallet).filter(Wallet.user_id == student.id).first()
    assert Decimal(str(wallet.balance)) == Decimal("150.00")


def test_after_escrow_escrow_lock_transaction_exists(db: Session) -> None:
    """After escrow, a WalletTransaction of type 'escrow_lock' exists."""
    student = _make_user(db, "student")
    researcher = _make_user(db, "researcher")
    _fund_wallet(db, student.id, Decimal("300.00"))
    job = _make_job(db, student.id)
    contract = _make_contract(db, student.id, researcher.id, job.id, price=Decimal("150.00"))
    db.commit()

    payment_service.create_escrow(db, contract.id, student.id, _escrow_request(contract.id))

    txn = (
        db.query(WalletTransaction)
        .filter(
            WalletTransaction.wallet_id == student.id,
            WalletTransaction.transaction_type == "escrow_lock",
        )
        .first()
    )
    assert txn is not None


def test_ledger_entries_created_for_escrow(db: Session) -> None:
    """Escrow creates ledger entries (double-entry)."""
    student = _make_user(db, "student")
    researcher = _make_user(db, "researcher")
    _fund_wallet(db, student.id, Decimal("300.00"))
    job = _make_job(db, student.id)
    contract = _make_contract(db, student.id, researcher.id, job.id, price=Decimal("150.00"))
    db.commit()

    payment_service.create_escrow(db, contract.id, student.id, _escrow_request(contract.id))

    entries = db.query(LedgerEntry).filter(
        LedgerEntry.transaction_ref == f"escrow:{contract.id}"
    ).all()
    assert len(entries) >= 2  # debit + credit


def test_release_after_escrow_credits_researcher(db: Session) -> None:
    """After release, researcher wallet is credited with escrowed amount."""
    student = _make_user(db, "student")
    researcher = _make_user(db, "researcher")
    _make_researcher_profile(db, researcher.id)
    _fund_wallet(db, student.id, Decimal("300.00"))
    job = _make_job(db, student.id)
    contract = _make_contract(db, student.id, researcher.id, job.id, price=Decimal("150.00"))
    db.commit()

    payment_service.create_escrow(db, contract.id, student.id, _escrow_request(contract.id))
    contract.status = "submitted"
    db.commit()

    payment_service.release_payment(db, contract.id, student.id)

    researcher_wallet = db.query(Wallet).filter(Wallet.user_id == researcher.id).first()
    assert Decimal(str(researcher_wallet.balance)) == Decimal("150.00")


def test_refund_after_escrow_credits_student_back(db: Session) -> None:
    """After refund, student wallet is credited back with the escrowed amount."""
    student = _make_user(db, "student")
    researcher = _make_user(db, "researcher")
    _fund_wallet(db, student.id, Decimal("300.00"))
    job = _make_job(db, student.id)
    contract = _make_contract(db, student.id, researcher.id, job.id, price=Decimal("150.00"))
    db.commit()

    payment_service.create_escrow(db, contract.id, student.id, _escrow_request(contract.id))

    wallet_before = db.query(Wallet).filter(Wallet.user_id == student.id).first()
    balance_after_escrow = Decimal(str(wallet_before.balance))  # 300 - 150 = 150

    payment_service.refund_payment(
        db, contract.id, student.id, "student", "test refund reason here"
    )

    db.refresh(wallet_before)
    assert Decimal(str(wallet_before.balance)) == balance_after_escrow + Decimal("150.00")


def test_request_payout_after_release(db: Session) -> None:
    """Researcher can request payout after receiving released funds."""
    from app.schemas.payment_schema import PayoutRequestSchema

    student = _make_user(db, "student")
    researcher = _make_user(db, "researcher")
    _make_researcher_profile(db, researcher.id)
    _fund_wallet(db, student.id, Decimal("500.00"))
    job = _make_job(db, student.id)
    contract = _make_contract(db, student.id, researcher.id, job.id, price=Decimal("200.00"))
    db.commit()

    payment_service.create_escrow(db, contract.id, student.id, _escrow_request(contract.id))
    contract.status = "submitted"
    db.commit()
    payment_service.release_payment(db, contract.id, student.id)

    payout_data = PayoutRequestSchema(amount=Decimal("50.00"), provider="stripe")
    payout = payment_service.request_payout(db, researcher.id, payout_data)

    assert payout.status == "pending"
    assert float(payout.amount) == 50.00


def test_payout_with_insufficient_balance_raises_402(db: Session) -> None:
    """request_payout raises 402 when researcher wallet balance is insufficient."""
    from app.schemas.payment_schema import PayoutRequestSchema

    researcher = _make_user(db, "researcher")
    _fund_wallet(db, researcher.id, Decimal("5.00"))
    db.commit()

    payout_data = PayoutRequestSchema(amount=Decimal("50.00"), provider="stripe")

    with pytest.raises(HTTPException) as exc_info:
        payment_service.request_payout(db, researcher.id, payout_data)
    assert exc_info.value.status_code == 402
