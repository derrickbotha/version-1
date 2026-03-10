"""
Unit tests for professor_service.submit_quality_review and related functions.
"""
import uuid
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.contract import Contract
from app.models.job import Job
from app.models.professor import (
    ProfessorProfile,
    QualityReview,
    ReviewQueueItem,
)
from app.models.user import User
from app.schemas.professor_schema import QualityReviewSubmit
from app.services import professor_service


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
        title="Review Test Job",
        description="A job for quality review tests",
        subject="Biology",
        academic_level="Masters",
        proposed_price=Decimal("100.00"),
        status="submitted",
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
    status: str = "submitted",
) -> Contract:
    contract = Contract(
        id=uuid.uuid4(),
        job_id=job_id,
        student_id=student_id,
        researcher_id=researcher_id,
        agreed_price=Decimal("100.00"),
        status=status,
    )
    db.add(contract)
    db.flush()
    return contract


def _make_approved_professor(db: Session) -> tuple[User, ProfessorProfile]:
    user = _make_user(db, "professor")
    prof = ProfessorProfile(
        id=uuid.uuid4(),
        user_id=user.id,
        status="approved",
        total_reviews_completed=0,
        avg_review_score_given=0,
        review_fee_per_job=Decimal("5.00"),
        expertise_areas=["Biology"],
        review_subjects=["Biology"],
    )
    db.add(prof)
    db.flush()
    return user, prof


def _make_pending_professor(db: Session) -> tuple[User, ProfessorProfile]:
    user = _make_user(db, "professor")
    prof = ProfessorProfile(
        id=uuid.uuid4(),
        user_id=user.id,
        status="pending",
        total_reviews_completed=0,
        avg_review_score_given=0,
        review_fee_per_job=Decimal("5.00"),
    )
    db.add(prof)
    db.flush()
    return user, prof


def _make_queue_item(
    db: Session,
    contract_id: uuid.UUID,
    professor_id: uuid.UUID,
    status: str = "in_progress",
) -> ReviewQueueItem:
    item = ReviewQueueItem(
        id=uuid.uuid4(),
        contract_id=contract_id,
        professor_id=professor_id,
        queue_type="quality_review",
        status=status,
    )
    db.add(item)
    db.flush()
    return item


def _review_data(score: int = 80, verdict: str = "approved") -> QualityReviewSubmit:
    return QualityReviewSubmit(
        score=score,
        feedback="This is a thorough and detailed feedback for the submitted work. " * 2,
        verdict=verdict,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_review_approved_verdict_sets_contract_completed(db: Session) -> None:
    """verdict=approved sets contract.status=completed."""
    student = _make_user(db, "student")
    researcher = _make_user(db, "researcher")
    prof_user, prof = _make_approved_professor(db)
    job = _make_job(db, student.id)
    contract = _make_contract(db, student.id, researcher.id, job.id, status="submitted")
    db.commit()

    professor_service.submit_quality_review(db, contract.id, prof_user.id, _review_data(verdict="approved"))

    db.refresh(contract)
    assert contract.status == "completed"


def test_review_revision_required_verdict_sets_contract_revision_requested(db: Session) -> None:
    """verdict=revision_required sets contract.status=revision_requested."""
    student = _make_user(db, "student")
    researcher = _make_user(db, "researcher")
    prof_user, prof = _make_approved_professor(db)
    job = _make_job(db, student.id)
    contract = _make_contract(db, student.id, researcher.id, job.id, status="submitted")
    db.commit()

    professor_service.submit_quality_review(
        db, contract.id, prof_user.id, _review_data(verdict="revision_required")
    )

    db.refresh(contract)
    assert contract.status == "revision_requested"


def test_review_rejected_verdict_sets_contract_disputed(db: Session) -> None:
    """verdict=rejected sets contract.status=disputed."""
    student = _make_user(db, "student")
    researcher = _make_user(db, "researcher")
    prof_user, prof = _make_approved_professor(db)
    job = _make_job(db, student.id)
    contract = _make_contract(db, student.id, researcher.id, job.id, status="submitted")
    db.commit()

    professor_service.submit_quality_review(
        db, contract.id, prof_user.id, _review_data(verdict="rejected")
    )

    db.refresh(contract)
    assert contract.status == "disputed"


def test_review_increments_total_reviews_completed(db: Session) -> None:
    """submit_quality_review increments professor.total_reviews_completed."""
    student = _make_user(db, "student")
    researcher = _make_user(db, "researcher")
    prof_user, prof = _make_approved_professor(db)
    job = _make_job(db, student.id)
    contract = _make_contract(db, student.id, researcher.id, job.id, status="submitted")
    db.commit()

    before = prof.total_reviews_completed
    professor_service.submit_quality_review(db, contract.id, prof_user.id, _review_data())

    db.refresh(prof)
    assert prof.total_reviews_completed == before + 1


def test_review_updates_avg_review_score(db: Session) -> None:
    """submit_quality_review updates professor.avg_review_score_given."""
    student = _make_user(db, "student")
    researcher = _make_user(db, "researcher")
    prof_user, prof = _make_approved_professor(db)
    job = _make_job(db, student.id)
    contract = _make_contract(db, student.id, researcher.id, job.id, status="submitted")
    db.commit()

    professor_service.submit_quality_review(
        db, contract.id, prof_user.id, _review_data(score=80, verdict="approved")
    )

    db.refresh(prof)
    assert float(prof.avg_review_score_given) == 80.0


def test_review_invalid_verdict_raises_422(db: Session) -> None:
    """submit_quality_review raises 422 for invalid verdict."""
    student = _make_user(db, "student")
    researcher = _make_user(db, "researcher")
    prof_user, prof = _make_approved_professor(db)
    job = _make_job(db, student.id)
    contract = _make_contract(db, student.id, researcher.id, job.id, status="submitted")
    db.commit()

    bad_data = QualityReviewSubmit(
        score=75,
        feedback="This is a thorough and detailed feedback for the submitted work. " * 2,
        verdict="not_valid_verdict",
    )
    with pytest.raises(HTTPException) as exc_info:
        professor_service.submit_quality_review(db, contract.id, prof_user.id, bad_data)
    assert exc_info.value.status_code == 422


def test_review_on_non_reviewable_contract_status_raises_409(db: Session) -> None:
    """Review on a contract with status=accepted raises 409."""
    student = _make_user(db, "student")
    researcher = _make_user(db, "researcher")
    prof_user, prof = _make_approved_professor(db)
    job = _make_job(db, student.id)
    contract = _make_contract(db, student.id, researcher.id, job.id, status="accepted")
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        professor_service.submit_quality_review(db, contract.id, prof_user.id, _review_data())
    assert exc_info.value.status_code == 409


def test_unapproved_professor_cannot_review(db: Session) -> None:
    """A professor with status=pending cannot submit a review."""
    student = _make_user(db, "student")
    researcher = _make_user(db, "researcher")
    prof_user, prof = _make_pending_professor(db)
    job = _make_job(db, student.id)
    contract = _make_contract(db, student.id, researcher.id, job.id, status="submitted")
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        professor_service.submit_quality_review(db, contract.id, prof_user.id, _review_data())
    assert exc_info.value.status_code == 403


def test_review_fee_is_set_from_professor_review_fee(db: Session) -> None:
    """Review.fee_amount is set to professor.review_fee_per_job."""
    student = _make_user(db, "student")
    researcher = _make_user(db, "researcher")
    prof_user, prof = _make_approved_professor(db)
    prof.review_fee_per_job = Decimal("7.50")
    db.commit()
    job = _make_job(db, student.id)
    contract = _make_contract(db, student.id, researcher.id, job.id, status="submitted")
    db.commit()

    review = professor_service.submit_quality_review(db, contract.id, prof_user.id, _review_data())

    assert float(review.fee_amount) == float(Decimal("7.50"))


def test_multiple_review_rounds_increment_round_number(db: Session) -> None:
    """Second review on same contract has round_number=2."""
    student = _make_user(db, "student")
    researcher = _make_user(db, "researcher")
    prof_user, prof = _make_approved_professor(db)
    job = _make_job(db, student.id)
    contract = _make_contract(db, student.id, researcher.id, job.id, status="submitted")
    db.commit()

    review1 = professor_service.submit_quality_review(
        db, contract.id, prof_user.id, _review_data(verdict="revision_required")
    )
    assert review1.round_number == 1

    # Contract is now revision_requested, which is a reviewable status
    review2 = professor_service.submit_quality_review(
        db, contract.id, prof_user.id, _review_data(verdict="approved")
    )
    assert review2.round_number == 2


def test_queue_item_marked_completed_after_review(db: Session) -> None:
    """Queue item with status=in_progress is marked completed after review."""
    student = _make_user(db, "student")
    researcher = _make_user(db, "researcher")
    prof_user, prof = _make_approved_professor(db)
    job = _make_job(db, student.id)
    contract = _make_contract(db, student.id, researcher.id, job.id, status="submitted")
    queue_item = _make_queue_item(db, contract.id, prof.id, status="in_progress")
    db.commit()

    professor_service.submit_quality_review(db, contract.id, prof_user.id, _review_data())

    db.refresh(queue_item)
    assert queue_item.status == "completed"


def test_get_reviews_by_professor_returns_correct_list(db: Session) -> None:
    """get_reviews_by_professor returns only the professor's reviews."""
    student = _make_user(db, "student")
    researcher = _make_user(db, "researcher")
    prof_user, prof = _make_approved_professor(db)
    job = _make_job(db, student.id)
    contract = _make_contract(db, student.id, researcher.id, job.id, status="submitted")
    db.commit()

    professor_service.submit_quality_review(db, contract.id, prof_user.id, _review_data())

    reviews = professor_service.get_reviews_by_professor(db, prof_user.id)
    assert len(reviews) == 1
    assert reviews[0].professor_id == prof.id


def test_get_contract_review_returns_correct_list(db: Session) -> None:
    """get_contract_review returns reviews for the given contract."""
    student = _make_user(db, "student")
    researcher = _make_user(db, "researcher")
    prof_user, prof = _make_approved_professor(db)
    job = _make_job(db, student.id)
    contract = _make_contract(db, student.id, researcher.id, job.id, status="submitted")
    db.commit()

    professor_service.submit_quality_review(db, contract.id, prof_user.id, _review_data())

    reviews = professor_service.get_contract_review(db, contract.id)
    assert len(reviews) == 1
    assert reviews[0].contract_id == contract.id
