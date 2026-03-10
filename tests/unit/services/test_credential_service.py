"""
Unit tests for professor_service credential functions.
"""
import uuid
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.professor import ProfessorProfile, ResearcherCredential
from app.models.user import User
from app.schemas.professor_schema import CredentialSubmit, CredentialVerifyAction
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


def _credential_data() -> CredentialSubmit:
    return CredentialSubmit(
        credential_type="masters_degree",
        institution_name="MIT",
        field_of_study="Computer Science",
        year_obtained=2020,
    )


# ---------------------------------------------------------------------------
# submit_credential
# ---------------------------------------------------------------------------

def test_submit_credential_creates_credential_with_pending_status(db: Session) -> None:
    """submit_credential creates ResearcherCredential with status=pending."""
    researcher = _make_user(db, "researcher")
    db.commit()

    cred = professor_service.submit_credential(db, researcher, _credential_data())

    assert cred.status == "pending"
    assert cred.researcher_id == researcher.id


def test_only_researchers_can_submit_credentials(db: Session) -> None:
    """submit_credential raises 403 for non-researcher users."""
    student = _make_user(db, "student")
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        professor_service.submit_credential(db, student, _credential_data())
    assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# get_pending_credentials
# ---------------------------------------------------------------------------

def test_get_pending_credentials_requires_approved_professor(db: Session) -> None:
    """get_pending_credentials raises 403 for a pending professor."""
    pending_prof_user, pending_prof = _make_pending_professor(db)
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        professor_service.get_pending_credentials(db, pending_prof_user.id)
    assert exc_info.value.status_code == 403


def test_get_pending_credentials_returns_pending_creds(db: Session) -> None:
    """get_pending_credentials returns credentials with pending status."""
    prof_user, prof = _make_approved_professor(db)
    researcher = _make_user(db, "researcher")
    db.commit()

    professor_service.submit_credential(db, researcher, _credential_data())

    creds = professor_service.get_pending_credentials(db, prof_user.id)
    assert len(creds) >= 1
    assert all(c.status == "pending" for c in creds)


# ---------------------------------------------------------------------------
# action_credential
# ---------------------------------------------------------------------------

def test_action_credential_verify_sets_status_verified(db: Session) -> None:
    """action=verify sets credential status to verified."""
    prof_user, prof = _make_approved_professor(db)
    researcher = _make_user(db, "researcher")
    db.commit()

    cred = professor_service.submit_credential(db, researcher, _credential_data())

    action = CredentialVerifyAction(action="verify")
    updated = professor_service.action_credential(db, cred.id, prof_user.id, action)

    assert updated.status == "verified"


def test_action_credential_reject_requires_rejection_reason(db: Session) -> None:
    """action=reject without rejection_reason raises 422."""
    prof_user, prof = _make_approved_professor(db)
    researcher = _make_user(db, "researcher")
    db.commit()

    cred = professor_service.submit_credential(db, researcher, _credential_data())

    action = CredentialVerifyAction(action="reject")
    with pytest.raises(HTTPException) as exc_info:
        professor_service.action_credential(db, cred.id, prof_user.id, action)
    assert exc_info.value.status_code == 422


def test_action_credential_reject_sets_status_rejected(db: Session) -> None:
    """action=reject with reason sets credential status to rejected."""
    prof_user, prof = _make_approved_professor(db)
    researcher = _make_user(db, "researcher")
    db.commit()

    cred = professor_service.submit_credential(db, researcher, _credential_data())

    action = CredentialVerifyAction(action="reject", rejection_reason="Invalid document")
    updated = professor_service.action_credential(db, cred.id, prof_user.id, action)

    assert updated.status == "rejected"
    assert updated.rejection_reason == "Invalid document"


def test_cannot_action_already_actioned_credential(db: Session) -> None:
    """action_credential raises 409 if credential is not pending."""
    prof_user, prof = _make_approved_professor(db)
    researcher = _make_user(db, "researcher")
    db.commit()

    cred = professor_service.submit_credential(db, researcher, _credential_data())

    # First action
    action = CredentialVerifyAction(action="verify")
    professor_service.action_credential(db, cred.id, prof_user.id, action)

    # Second action should fail
    with pytest.raises(HTTPException) as exc_info:
        professor_service.action_credential(db, cred.id, prof_user.id, action)
    assert exc_info.value.status_code == 409


def test_get_researcher_credentials_returns_all_credentials(db: Session) -> None:
    """get_researcher_credentials returns all credentials for researcher."""
    prof_user, prof = _make_approved_professor(db)
    researcher = _make_user(db, "researcher")
    db.commit()

    professor_service.submit_credential(db, researcher, _credential_data())
    professor_service.submit_credential(
        db, researcher,
        CredentialSubmit(
            credential_type="phd",
            institution_name="Stanford",
            field_of_study="Machine Learning",
        )
    )

    creds = professor_service.get_researcher_credentials(db, researcher.id)
    assert len(creds) == 2


def test_verified_credential_records_verified_by_id_and_verified_at(db: Session) -> None:
    """Verified credential has verified_by_id and verified_at set."""
    prof_user, prof = _make_approved_professor(db)
    researcher = _make_user(db, "researcher")
    db.commit()

    cred = professor_service.submit_credential(db, researcher, _credential_data())

    action = CredentialVerifyAction(action="verify")
    updated = professor_service.action_credential(db, cred.id, prof_user.id, action)

    assert updated.verified_by_id == prof.id
    assert updated.verified_at is not None


def test_rejected_credential_records_rejection_reason(db: Session) -> None:
    """Rejected credential records the rejection reason."""
    prof_user, prof = _make_approved_professor(db)
    researcher = _make_user(db, "researcher")
    db.commit()

    cred = professor_service.submit_credential(db, researcher, _credential_data())

    reason = "Document appears to be a forgery"
    action = CredentialVerifyAction(action="reject", rejection_reason=reason)
    updated = professor_service.action_credential(db, cred.id, prof_user.id, action)

    assert updated.rejection_reason == reason


def test_submit_credential_stores_credential_type(db: Session) -> None:
    """submit_credential stores the correct credential_type."""
    researcher = _make_user(db, "researcher")
    db.commit()

    cred = professor_service.submit_credential(db, researcher, _credential_data())

    assert cred.credential_type == "masters_degree"


def test_submit_credential_stores_institution_name(db: Session) -> None:
    """submit_credential stores the institution_name."""
    researcher = _make_user(db, "researcher")
    db.commit()

    cred = professor_service.submit_credential(db, researcher, _credential_data())

    assert cred.institution_name == "MIT"
