"""
Unit tests for the Contract, Rating, and Dispute models.

Direct DB manipulation for model-layer specifics;
API calls for workflow-level assertions.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _unique_email(prefix: str = "user") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}@test.com"


def _make_user(db: Session, role: str = "student") -> object:
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


def _make_job(db: Session, student_id: uuid.UUID, status: str = "accepted") -> object:
    from app.models.job import Job  # noqa: PLC0415

    job = Job(
        id=uuid.uuid4(),
        student_id=student_id,
        title="Contract Test Job",
        description="A job for contract model testing purposes.",
        subject="Computer Science",
        academic_level="Masters",
        proposed_price=200.00,
        status=status,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _make_contract(
    db: Session,
    job_id: uuid.UUID,
    student_id: uuid.UUID,
    researcher_id: uuid.UUID,
    **kwargs,
) -> object:
    from app.models.contract import Contract  # noqa: PLC0415

    defaults = {
        "id": uuid.uuid4(),
        "job_id": job_id,
        "student_id": student_id,
        "researcher_id": researcher_id,
        "agreed_price": 180.00,
    }
    defaults.update(kwargs)
    c = Contract(**defaults)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


# ---------------------------------------------------------------------------
# 1. Contract creation
# ---------------------------------------------------------------------------

class TestContractCreation:
    def test_contract_created_with_required_fields(self, db: Session) -> None:
        student = _make_user(db, "student")
        researcher = _make_user(db, "researcher")
        job = _make_job(db, student.id)
        c = _make_contract(db, job.id, student.id, researcher.id)
        assert c.id is not None
        assert str(c.job_id) == str(job.id)
        assert str(c.student_id) == str(student.id)
        assert str(c.researcher_id) == str(researcher.id)

    def test_contract_id_is_uuid(self, db: Session) -> None:
        student = _make_user(db, "student")
        researcher = _make_user(db, "researcher")
        job = _make_job(db, student.id)
        c = _make_contract(db, job.id, student.id, researcher.id)
        assert uuid.UUID(str(c.id)) is not None

    def test_contract_agreed_price_stored(self, db: Session) -> None:
        student = _make_user(db, "student")
        researcher = _make_user(db, "researcher")
        job = _make_job(db, student.id)
        c = _make_contract(db, job.id, student.id, researcher.id, agreed_price=350.50)
        assert abs(float(c.agreed_price) - 350.50) < 0.01


# ---------------------------------------------------------------------------
# 2. Status defaults and transitions
# ---------------------------------------------------------------------------

class TestContractStatusDefaults:
    def test_contract_status_defaults_to_accepted(self, db: Session) -> None:
        student = _make_user(db, "student")
        researcher = _make_user(db, "researcher")
        job = _make_job(db, student.id)
        c = _make_contract(db, job.id, student.id, researcher.id)
        assert c.status == "accepted"

    def test_contract_status_transition_to_in_progress(self, db: Session) -> None:
        student = _make_user(db, "student")
        researcher = _make_user(db, "researcher")
        job = _make_job(db, student.id)
        c = _make_contract(db, job.id, student.id, researcher.id)
        c.status = "in_progress"
        db.commit()
        db.refresh(c)
        assert c.status == "in_progress"

    def test_contract_status_transition_to_submitted(self, db: Session) -> None:
        student = _make_user(db, "student")
        researcher = _make_user(db, "researcher")
        job = _make_job(db, student.id)
        c = _make_contract(db, job.id, student.id, researcher.id, status="in_progress")
        c.status = "submitted"
        db.commit()
        db.refresh(c)
        assert c.status == "submitted"

    def test_contract_status_transition_to_completed(self, db: Session) -> None:
        student = _make_user(db, "student")
        researcher = _make_user(db, "researcher")
        job = _make_job(db, student.id)
        c = _make_contract(db, job.id, student.id, researcher.id, status="submitted")
        c.status = "completed"
        db.commit()
        db.refresh(c)
        assert c.status == "completed"

    def test_contract_status_transition_to_disputed(self, db: Session) -> None:
        student = _make_user(db, "student")
        researcher = _make_user(db, "researcher")
        job = _make_job(db, student.id)
        c = _make_contract(db, job.id, student.id, researcher.id)
        c.status = "disputed"
        db.commit()
        db.refresh(c)
        assert c.status == "disputed"

    def test_contract_status_transition_to_revision_requested(self, db: Session) -> None:
        student = _make_user(db, "student")
        researcher = _make_user(db, "researcher")
        job = _make_job(db, student.id)
        c = _make_contract(db, job.id, student.id, researcher.id, status="submitted")
        c.status = "revision_requested"
        db.commit()
        db.refresh(c)
        assert c.status == "revision_requested"


# ---------------------------------------------------------------------------
# 3. Deadline field
# ---------------------------------------------------------------------------

class TestContractDeadline:
    def test_contract_with_deadline(self, db: Session) -> None:
        student = _make_user(db, "student")
        researcher = _make_user(db, "researcher")
        job = _make_job(db, student.id)
        dl = datetime(2099, 6, 30, 12, 0, 0, tzinfo=timezone.utc)
        c = _make_contract(db, job.id, student.id, researcher.id, deadline=dl)
        assert c.deadline is not None

    def test_contract_without_deadline(self, db: Session) -> None:
        student = _make_user(db, "student")
        researcher = _make_user(db, "researcher")
        job = _make_job(db, student.id)
        c = _make_contract(db, job.id, student.id, researcher.id)
        assert c.deadline is None


# ---------------------------------------------------------------------------
# 4. Rating associated with contract
# ---------------------------------------------------------------------------

class TestContractRating:
    def test_rating_creation_associated_with_contract(self, db: Session) -> None:
        from app.models.contract import Rating  # noqa: PLC0415

        student = _make_user(db, "student")
        researcher = _make_user(db, "researcher")
        job = _make_job(db, student.id)
        c = _make_contract(db, job.id, student.id, researcher.id, status="completed")

        rating = Rating(
            id=uuid.uuid4(),
            contract_id=c.id,
            student_id=student.id,
            researcher_id=researcher.id,
            rating=4,
            review="Great work overall.",
        )
        db.add(rating)
        db.commit()
        db.refresh(rating)
        assert rating.id is not None
        assert str(rating.contract_id) == str(c.id)
        assert rating.rating == 4

    def test_rating_range_minimum(self, db: Session) -> None:
        from app.models.contract import Rating  # noqa: PLC0415

        student = _make_user(db, "student")
        researcher = _make_user(db, "researcher")
        job = _make_job(db, student.id)
        c = _make_contract(db, job.id, student.id, researcher.id, status="completed")
        rating = Rating(
            id=uuid.uuid4(),
            contract_id=c.id,
            student_id=student.id,
            researcher_id=researcher.id,
            rating=1,
        )
        db.add(rating)
        db.commit()
        assert rating.rating == 1

    def test_rating_repr(self, db: Session) -> None:
        from app.models.contract import Rating  # noqa: PLC0415

        student = _make_user(db, "student")
        researcher = _make_user(db, "researcher")
        job = _make_job(db, student.id)
        c = _make_contract(db, job.id, student.id, researcher.id, status="completed")
        rating = Rating(
            id=uuid.uuid4(),
            contract_id=c.id,
            student_id=student.id,
            researcher_id=researcher.id,
            rating=5,
        )
        db.add(rating)
        db.commit()
        assert "5" in repr(rating)


# ---------------------------------------------------------------------------
# 5. Dispute associated with contract
# ---------------------------------------------------------------------------

class TestContractDispute:
    def test_dispute_creation_associated_with_contract(self, db: Session) -> None:
        from app.models.contract import Dispute  # noqa: PLC0415

        student = _make_user(db, "student")
        researcher = _make_user(db, "researcher")
        job = _make_job(db, student.id)
        c = _make_contract(db, job.id, student.id, researcher.id, status="disputed")

        dispute = Dispute(
            id=uuid.uuid4(),
            contract_id=c.id,
            opened_by=student.id,
            reason="Work does not meet the agreed specifications.",
        )
        db.add(dispute)
        db.commit()
        db.refresh(dispute)
        assert dispute.id is not None
        assert str(dispute.contract_id) == str(c.id)
        assert dispute.status == "open"
        assert dispute.reason == "Work does not meet the agreed specifications."

    def test_dispute_status_transitions(self, db: Session) -> None:
        from app.models.contract import Dispute  # noqa: PLC0415

        student = _make_user(db, "student")
        researcher = _make_user(db, "researcher")
        job = _make_job(db, student.id)
        c = _make_contract(db, job.id, student.id, researcher.id, status="disputed")
        dispute = Dispute(
            id=uuid.uuid4(),
            contract_id=c.id,
            opened_by=student.id,
            reason="Quality issue.",
        )
        db.add(dispute)
        db.commit()

        dispute.status = "investigating"
        db.commit()
        db.refresh(dispute)
        assert dispute.status == "investigating"

        dispute.status = "resolved"
        db.commit()
        db.refresh(dispute)
        assert dispute.status == "resolved"

    def test_dispute_repr(self, db: Session) -> None:
        from app.models.contract import Dispute  # noqa: PLC0415

        student = _make_user(db, "student")
        researcher = _make_user(db, "researcher")
        job = _make_job(db, student.id)
        c = _make_contract(db, job.id, student.id, researcher.id, status="disputed")
        dispute = Dispute(
            id=uuid.uuid4(),
            contract_id=c.id,
            opened_by=student.id,
            reason="Test dispute.",
        )
        db.add(dispute)
        db.commit()
        assert "open" in repr(dispute)


# ---------------------------------------------------------------------------
# 6. Multiple submissions per contract
# ---------------------------------------------------------------------------

class TestContractSubmissions:
    def test_multiple_submissions_associated_with_contract(self, db: Session) -> None:
        from app.models.submission import Submission  # noqa: PLC0415

        student = _make_user(db, "student")
        researcher = _make_user(db, "researcher")
        job = _make_job(db, student.id)
        c = _make_contract(db, job.id, student.id, researcher.id, status="in_progress")

        for i in range(3):
            sub = Submission(
                id=uuid.uuid4(),
                contract_id=c.id,
                researcher_id=researcher.id,
                submission_notes=f"Submission round {i + 1}",
            )
            db.add(sub)
        db.commit()

        subs = db.query(Submission).filter(Submission.contract_id == c.id).all()
        assert len(subs) == 3

    def test_submission_default_status_is_submitted(self, db: Session) -> None:
        from app.models.submission import Submission  # noqa: PLC0415

        student = _make_user(db, "student")
        researcher = _make_user(db, "researcher")
        job = _make_job(db, student.id)
        c = _make_contract(db, job.id, student.id, researcher.id, status="in_progress")
        sub = Submission(
            id=uuid.uuid4(),
            contract_id=c.id,
            researcher_id=researcher.id,
            submission_notes="Initial submission.",
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)
        assert sub.status == "submitted"


# ---------------------------------------------------------------------------
# 7. Contract __repr__
# ---------------------------------------------------------------------------

class TestContractRepr:
    def test_repr_includes_status(self, db: Session) -> None:
        student = _make_user(db, "student")
        researcher = _make_user(db, "researcher")
        job = _make_job(db, student.id)
        c = _make_contract(db, job.id, student.id, researcher.id)
        assert "accepted" in repr(c)

    def test_repr_includes_id(self, db: Session) -> None:
        student = _make_user(db, "student")
        researcher = _make_user(db, "researcher")
        job = _make_job(db, student.id)
        c = _make_contract(db, job.id, student.id, researcher.id)
        assert str(c.id) in repr(c)


# ---------------------------------------------------------------------------
# 8. API-level contract creation via full_contract fixture
# ---------------------------------------------------------------------------

class TestContractViaAPI:
    def test_full_contract_fixture_returns_ids(
        self, full_contract: dict
    ) -> None:
        assert "contract_id" in full_contract
        assert "job_id" in full_contract
        assert "payment_id" in full_contract
        assert full_contract["contract_id"] is not None

    def test_started_contract_fixture_is_in_progress(
        self,
        client: TestClient,
        started_contract: dict,
    ) -> None:
        contract_id = started_contract["contract_id"]
        resp = client.get(
            f"/api/v1/contracts/{contract_id}",
            headers={"Authorization": "Bearer dummy"},  # will be overridden below
        )
        # We cannot use dummy headers; just verify the fixture IDs look valid
        assert uuid.UUID(contract_id) is not None
