"""
Unit tests for the ProfessorProfile, Institution, and related professor models.

Uses direct DB manipulation for model-layer specifics and API calls
where workflow-level verification is required.
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _unique_email(prefix: str = "user") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}@test.com"


def _make_user(db: Session, role: str = "professor") -> object:
    from app.models.user import User
    from app.services.auth_service import hash_password  # noqa: PLC0415

    u = User(
        id=uuid.uuid4(),
        email=_unique_email(role),
        password_hash=hash_password("TestPassword123!"),
        first_name=role.capitalize(),
        last_name="Tester",
        role=role,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _make_institution(db: Session, name: str | None = None, **kwargs) -> object:
    from app.models.professor import Institution  # noqa: PLC0415

    inst = Institution(
        id=uuid.uuid4(),
        name=name or f"Test University {uuid.uuid4().hex[:6]}",
        country=kwargs.get("country", "South Africa"),
        domain=kwargs.get("domain", "testuni.ac.za"),
        is_verified=kwargs.get("is_verified", False),
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return inst


def _make_professor_profile(db: Session, user_id: uuid.UUID, **kwargs) -> object:
    from app.models.professor import ProfessorProfile  # noqa: PLC0415

    defaults = {
        "id": uuid.uuid4(),
        "user_id": user_id,
        "title": "Dr.",
        "department": "Computer Science",
        "bio": "A test professor bio.",
        "expertise_areas": ["Machine Learning", "AI"],
        "review_subjects": ["Computer Science"],
    }
    defaults.update(kwargs)
    prof = ProfessorProfile(**defaults)
    db.add(prof)
    db.commit()
    db.refresh(prof)
    return prof


# ---------------------------------------------------------------------------
# 1. ProfessorProfile creation
# ---------------------------------------------------------------------------

class TestProfessorProfileCreation:
    def test_professor_profile_created(self, db: Session) -> None:
        user = _make_user(db, "professor")
        prof = _make_professor_profile(db, user.id)
        assert prof.id is not None
        assert str(prof.user_id) == str(user.id)

    def test_professor_profile_id_is_uuid(self, db: Session) -> None:
        user = _make_user(db, "professor")
        prof = _make_professor_profile(db, user.id)
        assert uuid.UUID(str(prof.id)) is not None

    def test_professor_profile_title_stored(self, db: Session) -> None:
        user = _make_user(db, "professor")
        prof = _make_professor_profile(db, user.id, title="Prof.")
        assert prof.title == "Prof."

    def test_professor_profile_department_stored(self, db: Session) -> None:
        user = _make_user(db, "professor")
        prof = _make_professor_profile(db, user.id, department="Mathematics")
        assert prof.department == "Mathematics"

    def test_professor_profile_bio_stored(self, db: Session) -> None:
        user = _make_user(db, "professor")
        prof = _make_professor_profile(db, user.id, bio="Expert in neural networks.")
        assert prof.bio == "Expert in neural networks."


# ---------------------------------------------------------------------------
# 2. Status defaults and transitions
# ---------------------------------------------------------------------------

class TestProfessorProfileStatusDefaults:
    def test_status_defaults_to_pending(self, db: Session) -> None:
        user = _make_user(db, "professor")
        prof = _make_professor_profile(db, user.id)
        assert prof.status == "pending"

    def test_status_transition_pending_to_approved(self, db: Session) -> None:
        user = _make_user(db, "professor")
        prof = _make_professor_profile(db, user.id)
        assert prof.status == "pending"
        prof.status = "approved"
        db.commit()
        db.refresh(prof)
        assert prof.status == "approved"

    def test_status_transition_pending_to_rejected(self, db: Session) -> None:
        user = _make_user(db, "professor")
        prof = _make_professor_profile(db, user.id)
        prof.status = "rejected"
        db.commit()
        db.refresh(prof)
        assert prof.status == "rejected"

    def test_status_transition_approved_to_suspended(self, db: Session) -> None:
        user = _make_user(db, "professor")
        prof = _make_professor_profile(db, user.id, status="approved")
        prof.status = "suspended"
        db.commit()
        db.refresh(prof)
        assert prof.status == "suspended"

    def test_status_api_create_starts_pending(
        self, client: TestClient, professor_headers: dict
    ) -> None:
        """Creating a profile via the API should start with pending status."""
        resp = client.post(
            "/api/v1/professor/profile",
            json={
                "bio": "API-created professor bio.",
                "title": "Dr.",
                "department": "Physics",
                "expertise_areas": ["Quantum Mechanics"],
                "review_subjects": ["Physics"],
            },
            headers=professor_headers,
        )
        assert resp.status_code in (200, 201), f"Create profile failed: {resp.text}"
        data = resp.json()
        assert data["status"] == "pending"


# ---------------------------------------------------------------------------
# 3. Institution creation and association
# ---------------------------------------------------------------------------

class TestInstitution:
    def test_institution_creation(self, db: Session) -> None:
        inst = _make_institution(db, "MIT")
        assert inst.id is not None
        assert inst.name == "MIT"

    def test_institution_defaults_to_unverified(self, db: Session) -> None:
        inst = _make_institution(db)
        assert inst.is_verified is False

    def test_institution_can_be_verified(self, db: Session) -> None:
        inst = _make_institution(db)
        inst.is_verified = True
        db.commit()
        db.refresh(inst)
        assert inst.is_verified is True

    def test_institution_country_stored(self, db: Session) -> None:
        inst = _make_institution(db, country="United Kingdom")
        assert inst.country == "United Kingdom"

    def test_institution_domain_stored(self, db: Session) -> None:
        inst = _make_institution(db, domain="oxford.ac.uk")
        assert inst.domain == "oxford.ac.uk"

    def test_institution_repr(self, db: Session) -> None:
        inst = _make_institution(db, "Cambridge")
        r = repr(inst)
        assert "Cambridge" in r

    def test_professor_profile_with_institution(self, db: Session) -> None:
        user = _make_user(db, "professor")
        inst = _make_institution(db, "Stanford")
        prof = _make_professor_profile(db, user.id, institution_id=inst.id)
        assert str(prof.institution_id) == str(inst.id)


# ---------------------------------------------------------------------------
# 4. expertise_areas and review_subjects as lists
# ---------------------------------------------------------------------------

class TestProfessorProfileLists:
    def test_expertise_areas_stored(self, db: Session) -> None:
        user = _make_user(db, "professor")
        areas = ["NLP", "Computer Vision", "Reinforcement Learning"]
        prof = _make_professor_profile(db, user.id, expertise_areas=areas)
        # Stored as JSON in SQLite; value should equal the original list
        stored = prof.expertise_areas
        assert stored == areas

    def test_review_subjects_stored(self, db: Session) -> None:
        user = _make_user(db, "professor")
        subjects = ["Computer Science", "Mathematics"]
        prof = _make_professor_profile(db, user.id, review_subjects=subjects)
        assert prof.review_subjects == subjects

    def test_expertise_areas_defaults_to_none_or_empty(self, db: Session) -> None:
        from app.models.professor import ProfessorProfile  # noqa: PLC0415

        user = _make_user(db, "professor")
        prof = ProfessorProfile(
            id=uuid.uuid4(),
            user_id=user.id,
        )
        db.add(prof)
        db.commit()
        db.refresh(prof)
        # Should be None or an empty list — both acceptable defaults
        assert prof.expertise_areas is None or prof.expertise_areas == []

    def test_review_subjects_can_be_updated(self, db: Session) -> None:
        user = _make_user(db, "professor")
        prof = _make_professor_profile(db, user.id, review_subjects=["Physics"])
        prof.review_subjects = ["Physics", "Chemistry"]
        db.commit()
        db.refresh(prof)
        assert "Chemistry" in prof.review_subjects


# ---------------------------------------------------------------------------
# 5. Numeric fields: total_reviews_completed and review_fee_per_job
# ---------------------------------------------------------------------------

class TestProfessorProfileNumericFields:
    def test_total_reviews_completed_defaults_to_zero(self, db: Session) -> None:
        user = _make_user(db, "professor")
        prof = _make_professor_profile(db, user.id)
        assert prof.total_reviews_completed == 0

    def test_review_fee_per_job_defaults_to_five(self, db: Session) -> None:
        user = _make_user(db, "professor")
        prof = _make_professor_profile(db, user.id)
        assert abs(float(prof.review_fee_per_job) - 5.00) < 0.01

    def test_review_fee_per_job_can_be_updated(self, db: Session) -> None:
        user = _make_user(db, "professor")
        prof = _make_professor_profile(db, user.id)
        prof.review_fee_per_job = 10.00
        db.commit()
        db.refresh(prof)
        assert abs(float(prof.review_fee_per_job) - 10.00) < 0.01

    def test_total_reviews_completed_can_be_incremented(self, db: Session) -> None:
        user = _make_user(db, "professor")
        prof = _make_professor_profile(db, user.id)
        prof.total_reviews_completed = 5
        db.commit()
        db.refresh(prof)
        assert prof.total_reviews_completed == 5


# ---------------------------------------------------------------------------
# 6. Optional string fields: orcid_id, linkedin_url
# ---------------------------------------------------------------------------

class TestProfessorProfileOptionalFields:
    def test_orcid_id_stored(self, db: Session) -> None:
        user = _make_user(db, "professor")
        prof = _make_professor_profile(db, user.id, orcid_id="0000-0002-1825-0097")
        assert prof.orcid_id == "0000-0002-1825-0097"

    def test_linkedin_url_stored(self, db: Session) -> None:
        user = _make_user(db, "professor")
        prof = _make_professor_profile(
            db, user.id, linkedin_url="https://linkedin.com/in/testprofessor"
        )
        assert prof.linkedin_url == "https://linkedin.com/in/testprofessor"

    def test_orcid_id_defaults_to_none(self, db: Session) -> None:
        user = _make_user(db, "professor")
        prof = _make_professor_profile(db, user.id)
        assert prof.orcid_id is None

    def test_institutional_email_stored(self, db: Session) -> None:
        user = _make_user(db, "professor")
        prof = _make_professor_profile(
            db, user.id, institutional_email="prof@university.ac.za"
        )
        assert prof.institutional_email == "prof@university.ac.za"


# ---------------------------------------------------------------------------
# 7. academic_rank field
# ---------------------------------------------------------------------------

class TestProfessorAcademicRank:
    def test_academic_rank_full_professor(self, db: Session) -> None:
        user = _make_user(db, "professor")
        prof = _make_professor_profile(db, user.id, academic_rank="full_professor")
        assert prof.academic_rank == "full_professor"

    def test_academic_rank_assistant_professor(self, db: Session) -> None:
        user = _make_user(db, "professor")
        prof = _make_professor_profile(db, user.id, academic_rank="assistant_professor")
        assert prof.academic_rank == "assistant_professor"

    def test_academic_rank_defaults_to_none(self, db: Session) -> None:
        user = _make_user(db, "professor")
        prof = _make_professor_profile(db, user.id)
        assert prof.academic_rank is None


# ---------------------------------------------------------------------------
# 8. ProfessorProfile __repr__
# ---------------------------------------------------------------------------

class TestProfessorProfileRepr:
    def test_repr_includes_user_id(self, db: Session) -> None:
        user = _make_user(db, "professor")
        prof = _make_professor_profile(db, user.id)
        assert str(user.id) in repr(prof)

    def test_repr_includes_status(self, db: Session) -> None:
        user = _make_user(db, "professor")
        prof = _make_professor_profile(db, user.id)
        assert "pending" in repr(prof)

    def test_repr_after_approval(self, db: Session) -> None:
        user = _make_user(db, "professor")
        prof = _make_professor_profile(db, user.id, status="approved")
        assert "approved" in repr(prof)


# ---------------------------------------------------------------------------
# 9. approved_professor_headers fixture integration
# ---------------------------------------------------------------------------

class TestApprovedProfessorViaAPI:
    def test_approved_professor_profile_via_fixture(
        self, client: TestClient, approved_professor_headers: dict
    ) -> None:
        """The approved_professor_headers fixture should yield a fully approved profile."""
        resp = client.get("/api/v1/professor/profile", headers=approved_professor_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "approved"

    def test_approved_professor_has_profile_id(
        self, client: TestClient, approved_professor_headers: dict
    ) -> None:
        resp = client.get("/api/v1/professor/profile", headers=approved_professor_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert uuid.UUID(data["id"]) is not None
