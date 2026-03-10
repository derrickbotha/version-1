"""
Unit tests for professor_service endorsement functions.
"""
import uuid
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.professor import ProfessorProfile, ProfessorEndorsement
from app.models.user import User
from app.schemas.professor_schema import EndorsementCreate
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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_create_endorsement_creates_professor_endorsement(db: Session) -> None:
    """create_endorsement creates a ProfessorEndorsement record."""
    prof_user, prof = _make_approved_professor(db)
    researcher = _make_user(db, "researcher")
    db.commit()

    data = EndorsementCreate(
        researcher_id=researcher.id,
        subject_area="Machine Learning",
        endorsement_text="Excellent researcher in ML.",
    )
    endorsement = professor_service.create_endorsement(db, prof_user.id, data)

    assert endorsement.professor_id == prof.id
    assert endorsement.researcher_id == researcher.id
    assert endorsement.subject_area == "Machine Learning"
    assert endorsement.is_active is True


def test_duplicate_endorsement_same_professor_researcher_subject_raises_409(db: Session) -> None:
    """Creating a duplicate endorsement (same professor+researcher+subject) raises 409."""
    prof_user, prof = _make_approved_professor(db)
    researcher = _make_user(db, "researcher")
    db.commit()

    data = EndorsementCreate(
        researcher_id=researcher.id,
        subject_area="Machine Learning",
    )
    professor_service.create_endorsement(db, prof_user.id, data)

    with pytest.raises(HTTPException) as exc_info:
        professor_service.create_endorsement(db, prof_user.id, data)
    assert exc_info.value.status_code == 409


def test_only_approved_professor_can_endorse(db: Session) -> None:
    """Pending professor cannot create an endorsement."""
    pending_prof_user, pending_prof = _make_pending_professor(db)
    researcher = _make_user(db, "researcher")
    db.commit()

    data = EndorsementCreate(
        researcher_id=researcher.id,
        subject_area="Physics",
    )
    with pytest.raises(HTTPException) as exc_info:
        professor_service.create_endorsement(db, pending_prof_user.id, data)
    assert exc_info.value.status_code == 403


def test_get_endorsements_for_researcher_returns_active_only(db: Session) -> None:
    """get_endorsements_for_researcher returns only is_active=True endorsements."""
    prof_user, prof = _make_approved_professor(db)
    researcher = _make_user(db, "researcher")
    db.commit()

    # Create and then revoke one endorsement
    data1 = EndorsementCreate(researcher_id=researcher.id, subject_area="Biology")
    e1 = professor_service.create_endorsement(db, prof_user.id, data1)
    professor_service.revoke_endorsement(db, e1.id, prof_user.id)

    # Create an active one
    data2 = EndorsementCreate(researcher_id=researcher.id, subject_area="Chemistry")
    professor_service.create_endorsement(db, prof_user.id, data2)

    active = professor_service.get_endorsements_for_researcher(db, researcher.id)
    assert all(e.is_active for e in active)
    assert len(active) == 1


def test_revoke_endorsement_sets_is_active_false(db: Session) -> None:
    """revoke_endorsement sets endorsement.is_active to False."""
    prof_user, prof = _make_approved_professor(db)
    researcher = _make_user(db, "researcher")
    db.commit()

    data = EndorsementCreate(researcher_id=researcher.id, subject_area="Mathematics")
    endorsement = professor_service.create_endorsement(db, prof_user.id, data)

    professor_service.revoke_endorsement(db, endorsement.id, prof_user.id)

    db.refresh(endorsement)
    assert endorsement.is_active is False


def test_revoke_endorsement_by_wrong_professor_raises_404(db: Session) -> None:
    """revoke_endorsement raises 404 when called by a different professor."""
    prof_user1, prof1 = _make_approved_professor(db)
    prof_user2, prof2 = _make_approved_professor(db)
    researcher = _make_user(db, "researcher")
    db.commit()

    data = EndorsementCreate(researcher_id=researcher.id, subject_area="Physics")
    endorsement = professor_service.create_endorsement(db, prof_user1.id, data)

    with pytest.raises(HTTPException) as exc_info:
        professor_service.revoke_endorsement(db, endorsement.id, prof_user2.id)
    assert exc_info.value.status_code == 404


def test_create_endorsement_with_non_researcher_target_raises_404(db: Session) -> None:
    """create_endorsement raises 404 when target is not a researcher."""
    prof_user, prof = _make_approved_professor(db)
    student = _make_user(db, "student")
    db.commit()

    data = EndorsementCreate(
        researcher_id=student.id,
        subject_area="Mathematics",
    )
    with pytest.raises(HTTPException) as exc_info:
        professor_service.create_endorsement(db, prof_user.id, data)
    assert exc_info.value.status_code == 404


def test_multiple_subject_areas_for_same_professor_researcher_allowed(db: Session) -> None:
    """Same professor can endorse same researcher for different subjects."""
    prof_user, prof = _make_approved_professor(db)
    researcher = _make_user(db, "researcher")
    db.commit()

    data1 = EndorsementCreate(researcher_id=researcher.id, subject_area="Mathematics")
    data2 = EndorsementCreate(researcher_id=researcher.id, subject_area="Physics")

    e1 = professor_service.create_endorsement(db, prof_user.id, data1)
    e2 = professor_service.create_endorsement(db, prof_user.id, data2)

    assert e1.subject_area == "Mathematics"
    assert e2.subject_area == "Physics"
    assert e1.id != e2.id
