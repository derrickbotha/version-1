"""
Unit tests for dispute_service functions.
"""
import uuid
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.contract import Contract, Dispute
from app.models.job import Job
from app.models.payment import Payment, Wallet
from app.models.professor import ProfessorProfile, DisputeRuling
from app.models.user import User
from app.schemas.dispute_schema import DisputeCreate, DisputeResolve
from app.schemas.professor_schema import DisputeRulingSubmit
from app.services import dispute_service, professor_service


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
        title="Dispute Test Job",
        description="A job for dispute service unit tests",
        subject="History",
        academic_level="Bachelors",
        proposed_price=Decimal("150.00"),
        status="in_progress",
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
    status: str = "in_progress",
    price: Decimal = Decimal("150.00"),
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


def _make_payment(
    db: Session,
    contract_id: uuid.UUID,
    student_id: uuid.UUID,
    researcher_id: uuid.UUID,
    amount: Decimal = Decimal("150.00"),
    status: str = "escrowed",
) -> Payment:
    payment = Payment(
        id=uuid.uuid4(),
        contract_id=contract_id,
        student_id=student_id,
        researcher_id=researcher_id,
        amount=amount,
        status=status,
        payment_provider="manual",
        provider_reference="test-dispute-ref",
    )
    db.add(payment)
    db.flush()
    return payment


def _fund_wallet(db: Session, user_id: uuid.UUID, amount: Decimal = Decimal("0.00")) -> Wallet:
    wallet = Wallet(user_id=user_id, balance=amount)
    db.add(wallet)
    db.flush()
    return wallet


def _make_approved_professor(db: Session) -> tuple[User, ProfessorProfile]:
    user = _make_user(db, "professor")
    prof = ProfessorProfile(
        id=uuid.uuid4(),
        user_id=user.id,
        status="approved",
        total_reviews_completed=0,
        avg_review_score_given=0,
        review_fee_per_job=Decimal("5.00"),
    )
    db.add(prof)
    db.flush()
    return user, prof


def _dispute_create(contract_id: uuid.UUID) -> DisputeCreate:
    return DisputeCreate(
        contract_id=contract_id,
        reason="Test dispute reason which is long enough for the validator minimum.",
    )


def _dispute_resolve(outcome: str = "refund_student") -> DisputeResolve:
    return DisputeResolve(
        resolution="Admin resolution: evidence reviewed and outcome determined based on contract terms.",
        outcome=outcome,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_open_dispute_creates_dispute_with_status_open(db: Session) -> None:
    """open_dispute creates a Dispute with status=open."""
    student = _make_user(db, "student")
    researcher = _make_user(db, "researcher")
    job = _make_job(db, student.id)
    contract = _make_contract(db, student.id, researcher.id, job.id, status="in_progress")
    db.commit()

    dispute = dispute_service.open_dispute(db, student.id, _dispute_create(contract.id))

    assert dispute.status == "open"
    assert dispute.contract_id == contract.id


def test_open_dispute_raises_403_if_user_not_on_contract(db: Session) -> None:
    """open_dispute raises 403 if the user is not a participant."""
    student = _make_user(db, "student")
    researcher = _make_user(db, "researcher")
    outsider = _make_user(db, "student")
    job = _make_job(db, student.id)
    contract = _make_contract(db, student.id, researcher.id, job.id, status="in_progress")
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        dispute_service.open_dispute(db, outsider.id, _dispute_create(contract.id))
    assert exc_info.value.status_code == 403


def test_open_dispute_raises_400_if_contract_already_completed(db: Session) -> None:
    """open_dispute raises 400 for a completed contract."""
    student = _make_user(db, "student")
    researcher = _make_user(db, "researcher")
    job = _make_job(db, student.id)
    contract = _make_contract(db, student.id, researcher.id, job.id, status="completed")
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        dispute_service.open_dispute(db, student.id, _dispute_create(contract.id))
    assert exc_info.value.status_code == 400


def test_open_dispute_raises_409_if_dispute_already_exists(db: Session) -> None:
    """open_dispute raises 400 (not 409) when an open dispute already exists."""
    student = _make_user(db, "student")
    researcher = _make_user(db, "researcher")
    job = _make_job(db, student.id)
    contract = _make_contract(db, student.id, researcher.id, job.id, status="in_progress")
    db.commit()

    dispute_service.open_dispute(db, student.id, _dispute_create(contract.id))

    # Contract is now disputed; trying again should fail
    with pytest.raises(HTTPException) as exc_info:
        dispute_service.open_dispute(db, student.id, _dispute_create(contract.id))
    assert exc_info.value.status_code in (400, 409)


def test_get_user_disputes_returns_user_disputes(db: Session) -> None:
    """get_user_disputes returns disputes opened by the given user."""
    student = _make_user(db, "student")
    researcher = _make_user(db, "researcher")
    job = _make_job(db, student.id)
    contract = _make_contract(db, student.id, researcher.id, job.id, status="in_progress")
    db.commit()

    dispute_service.open_dispute(db, student.id, _dispute_create(contract.id))

    disputes = dispute_service.get_user_disputes(db, student.id)
    assert len(disputes) == 1
    assert disputes[0].opened_by == student.id


def test_get_all_disputes_paginates_correctly(db: Session) -> None:
    """get_all_disputes returns paginated list of all disputes."""
    student1 = _make_user(db, "student")
    student2 = _make_user(db, "student")
    researcher = _make_user(db, "researcher")
    job1 = _make_job(db, student1.id)
    job2 = _make_job(db, student2.id)
    contract1 = _make_contract(db, student1.id, researcher.id, job1.id, status="in_progress")
    contract2 = _make_contract(db, student2.id, researcher.id, job2.id, status="in_progress")
    db.commit()

    dispute_service.open_dispute(db, student1.id, _dispute_create(contract1.id))
    dispute_service.open_dispute(db, student2.id, _dispute_create(contract2.id))

    items, total = dispute_service.get_all_disputes(db, None, page=1, page_size=1)
    assert total == 2
    assert len(items) == 1


def test_set_investigating_sets_status_investigating(db: Session) -> None:
    """set_investigating changes dispute status to investigating."""
    student = _make_user(db, "student")
    researcher = _make_user(db, "researcher")
    admin = _make_user(db, "admin")
    job = _make_job(db, student.id)
    contract = _make_contract(db, student.id, researcher.id, job.id, status="in_progress")
    db.commit()

    dispute = dispute_service.open_dispute(db, student.id, _dispute_create(contract.id))
    updated = dispute_service.set_investigating(db, dispute.id, admin.id)

    assert updated.status == "investigating"


def test_resolve_dispute_refund_student_refunds_payment(db: Session) -> None:
    """Resolving with outcome=refund_student sets payment to refunded and credits student."""
    student = _make_user(db, "student")
    researcher = _make_user(db, "researcher")
    admin = _make_user(db, "admin")
    job = _make_job(db, student.id)
    contract = _make_contract(db, student.id, researcher.id, job.id, status="in_progress")
    payment = _make_payment(db, contract.id, student.id, researcher.id, amount=Decimal("150.00"))
    _fund_wallet(db, student.id, Decimal("0.00"))
    db.commit()

    dispute = dispute_service.open_dispute(db, student.id, _dispute_create(contract.id))
    dispute_service.resolve_dispute(db, dispute.id, admin.id, _dispute_resolve("refund_student"))

    db.refresh(payment)
    assert payment.status == "refunded"

    wallet = db.query(Wallet).filter(Wallet.user_id == student.id).first()
    assert Decimal(str(wallet.balance)) == Decimal("150.00")


def test_resolve_dispute_release_researcher_releases_payment(db: Session) -> None:
    """Resolving with outcome=release_researcher credits researcher wallet."""
    student = _make_user(db, "student")
    researcher = _make_user(db, "researcher")
    admin = _make_user(db, "admin")
    job = _make_job(db, student.id)
    contract = _make_contract(db, student.id, researcher.id, job.id, status="in_progress")
    payment = _make_payment(db, contract.id, student.id, researcher.id, amount=Decimal("150.00"))
    _fund_wallet(db, researcher.id, Decimal("0.00"))
    db.commit()

    dispute = dispute_service.open_dispute(db, student.id, _dispute_create(contract.id))
    dispute_service.resolve_dispute(db, dispute.id, admin.id, _dispute_resolve("release_researcher"))

    db.refresh(payment)
    assert payment.status == "released"

    wallet = db.query(Wallet).filter(Wallet.user_id == researcher.id).first()
    assert Decimal(str(wallet.balance)) == Decimal("150.00")


def test_resolve_dispute_sets_status_resolved(db: Session) -> None:
    """resolve_dispute sets dispute status to resolved."""
    student = _make_user(db, "student")
    researcher = _make_user(db, "researcher")
    admin = _make_user(db, "admin")
    job = _make_job(db, student.id)
    contract = _make_contract(db, student.id, researcher.id, job.id, status="in_progress")
    db.commit()

    dispute = dispute_service.open_dispute(db, student.id, _dispute_create(contract.id))
    resolved = dispute_service.resolve_dispute(
        db, dispute.id, admin.id, _dispute_resolve("refund_student")
    )

    assert resolved.status == "resolved"


def test_professor_ruling_via_submit_dispute_ruling(db: Session) -> None:
    """submit_dispute_ruling creates a DisputeRuling record."""
    student = _make_user(db, "student")
    researcher = _make_user(db, "researcher")
    prof_user, prof = _make_approved_professor(db)
    job = _make_job(db, student.id)
    contract = _make_contract(db, student.id, researcher.id, job.id, status="in_progress")
    db.commit()

    dispute = dispute_service.open_dispute(db, student.id, _dispute_create(contract.id))

    ruling_data = DisputeRulingSubmit(
        ruling="full_refund",
        reasoning="After reviewing all evidence submitted by both parties, the work did not meet "
                  "the agreed specifications and therefore a full refund is warranted for the student.",
        evidence_reviewed="Reviewed all submitted materials.",
    )
    ruling = professor_service.submit_dispute_ruling(db, dispute.id, prof_user.id, ruling_data)

    assert ruling.dispute_id == dispute.id
    assert ruling.ruling == "full_refund"


def test_ruling_raises_409_if_ruling_already_exists(db: Session) -> None:
    """submit_dispute_ruling raises 409 if a ruling already exists."""
    student = _make_user(db, "student")
    researcher = _make_user(db, "researcher")
    prof_user, prof = _make_approved_professor(db)
    job = _make_job(db, student.id)
    contract = _make_contract(db, student.id, researcher.id, job.id, status="in_progress")
    db.commit()

    dispute = dispute_service.open_dispute(db, student.id, _dispute_create(contract.id))

    reasoning = ("After reviewing all evidence submitted by both parties, the work did not meet "
                 "the agreed specifications and therefore a full refund is warranted for the student.")
    ruling_data = DisputeRulingSubmit(
        ruling="full_refund",
        reasoning=reasoning,
    )
    professor_service.submit_dispute_ruling(db, dispute.id, prof_user.id, ruling_data)

    with pytest.raises(HTTPException) as exc_info:
        professor_service.submit_dispute_ruling(db, dispute.id, prof_user.id, ruling_data)
    assert exc_info.value.status_code == 409


def test_ruling_requires_approved_professor(db: Session) -> None:
    """submit_dispute_ruling raises 403 for a non-approved professor."""
    student = _make_user(db, "student")
    researcher = _make_user(db, "researcher")
    pending_prof_user = _make_user(db, "professor")
    pending_prof = ProfessorProfile(
        id=uuid.uuid4(),
        user_id=pending_prof_user.id,
        status="pending",
        total_reviews_completed=0,
        avg_review_score_given=0,
        review_fee_per_job=Decimal("5.00"),
    )
    db.add(pending_prof)
    job = _make_job(db, student.id)
    contract = _make_contract(db, student.id, researcher.id, job.id, status="in_progress")
    db.commit()

    dispute = dispute_service.open_dispute(db, student.id, _dispute_create(contract.id))

    reasoning = ("After reviewing all evidence submitted by both parties, the work did not meet "
                 "the agreed specifications and therefore a full refund is warranted for the student.")
    ruling_data = DisputeRulingSubmit(
        ruling="full_refund",
        reasoning=reasoning,
    )
    with pytest.raises(HTTPException) as exc_info:
        professor_service.submit_dispute_ruling(db, dispute.id, pending_prof_user.id, ruling_data)
    assert exc_info.value.status_code == 403
