"""
Unit tests for the Job and JobFile models.

Mix of direct DB manipulation (for model-layer specifics) and API calls
(for integration-level status transitions).
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


def _make_student(db: Session) -> object:
    """Insert a minimal student User directly into the DB."""
    from app.models.user import User
    from app.services.auth_service import hash_password  # noqa: PLC0415

    u = User(
        id=uuid.uuid4(),
        email=_unique_email("student"),
        password_hash=hash_password("TestPassword123!"),
        first_name="Student",
        last_name="Tester",
        role="student",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _make_job(db: Session, student_id: uuid.UUID, **kwargs) -> object:
    """Insert a Job directly into the DB."""
    from app.models.job import Job  # noqa: PLC0415

    defaults = {
        "id": uuid.uuid4(),
        "student_id": student_id,
        "title": "Test Research Job",
        "description": "A test research job description with enough text.",
        "subject": "Computer Science",
        "academic_level": "Masters",
        "proposed_price": 150.00,
    }
    defaults.update(kwargs)
    job = Job(**defaults)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _post_job_via_api(client: TestClient, headers: dict, **overrides) -> dict:
    payload = {
        "title": "API Test Job",
        "description": "A research job posted via the API for testing purposes.",
        "subject": "Physics",
        "academic_level": "PhD",
        "proposed_price": "200.00",
        "deadline": "2099-12-31T23:59:59Z",
    }
    payload.update(overrides)
    resp = client.post("/api/v1/jobs", json=payload, headers=headers)
    assert resp.status_code in (200, 201), f"Create job failed: {resp.text}"
    return resp.json()["data"]


# ---------------------------------------------------------------------------
# 1. Job creation with required fields
# ---------------------------------------------------------------------------

class TestJobCreation:
    def test_job_created_with_required_fields(self, db: Session) -> None:
        student = _make_student(db)
        job = _make_job(db, student.id)
        assert job.id is not None
        assert job.title == "Test Research Job"
        assert job.subject == "Computer Science"
        assert job.academic_level == "Masters"
        assert float(job.proposed_price) == 150.00

    def test_job_student_id_set(self, db: Session) -> None:
        student = _make_student(db)
        job = _make_job(db, student.id)
        assert str(job.student_id) == str(student.id)

    def test_job_id_is_uuid(self, db: Session) -> None:
        student = _make_student(db)
        job = _make_job(db, student.id)
        assert uuid.UUID(str(job.id)) is not None

    def test_multiple_jobs_per_student(self, db: Session) -> None:
        student = _make_student(db)
        j1 = _make_job(db, student.id, title="Job 1")
        j2 = _make_job(db, student.id, title="Job 2")
        j3 = _make_job(db, student.id, title="Job 3")
        assert j1.id != j2.id != j3.id
        assert str(j1.student_id) == str(student.id)
        assert str(j3.student_id) == str(student.id)


# ---------------------------------------------------------------------------
# 2. Status defaults
# ---------------------------------------------------------------------------

class TestJobStatusDefaults:
    def test_job_status_defaults_to_draft(self, db: Session) -> None:
        student = _make_student(db)
        job = _make_job(db, student.id)
        assert job.status == "draft"

    def test_job_status_can_be_set_to_open(self, db: Session) -> None:
        student = _make_student(db)
        job = _make_job(db, student.id, status="open")
        assert job.status == "open"

    def test_api_job_status_is_open(self, client: TestClient, student_headers: dict) -> None:
        """Jobs created via the API should start as open (not draft)."""
        data = _post_job_via_api(client, student_headers)
        assert data["status"] == "open"


# ---------------------------------------------------------------------------
# 3. Status transitions
# ---------------------------------------------------------------------------

class TestJobStatusTransitions:
    def test_transition_draft_to_open(self, db: Session) -> None:
        student = _make_student(db)
        job = _make_job(db, student.id, status="draft")
        job.status = "open"
        db.commit()
        db.refresh(job)
        assert job.status == "open"

    def test_transition_open_to_negotiation(self, db: Session) -> None:
        student = _make_student(db)
        job = _make_job(db, student.id, status="open")
        job.status = "negotiation"
        db.commit()
        db.refresh(job)
        assert job.status == "negotiation"

    def test_transition_negotiation_to_accepted(self, db: Session) -> None:
        student = _make_student(db)
        job = _make_job(db, student.id, status="negotiation")
        job.status = "accepted"
        db.commit()
        db.refresh(job)
        assert job.status == "accepted"

    def test_transition_accepted_to_in_progress(self, db: Session) -> None:
        student = _make_student(db)
        job = _make_job(db, student.id, status="accepted")
        job.status = "in_progress"
        db.commit()
        db.refresh(job)
        assert job.status == "in_progress"

    def test_transition_in_progress_to_submitted(self, db: Session) -> None:
        student = _make_student(db)
        job = _make_job(db, student.id, status="in_progress")
        job.status = "submitted"
        db.commit()
        db.refresh(job)
        assert job.status == "submitted"

    def test_transition_submitted_to_completed(self, db: Session) -> None:
        student = _make_student(db)
        job = _make_job(db, student.id, status="submitted")
        job.status = "completed"
        db.commit()
        db.refresh(job)
        assert job.status == "completed"

    def test_transition_to_disputed(self, db: Session) -> None:
        student = _make_student(db)
        job = _make_job(db, student.id, status="in_progress")
        job.status = "disputed"
        db.commit()
        db.refresh(job)
        assert job.status == "disputed"

    def test_transition_to_cancelled(self, db: Session) -> None:
        student = _make_student(db)
        job = _make_job(db, student.id, status="open")
        job.status = "cancelled"
        db.commit()
        db.refresh(job)
        assert job.status == "cancelled"


# ---------------------------------------------------------------------------
# 4. Deadline field
# ---------------------------------------------------------------------------

class TestJobDeadline:
    def test_job_with_deadline(self, db: Session) -> None:
        student = _make_student(db)
        dl = datetime(2099, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        job = _make_job(db, student.id, deadline=dl)
        assert job.deadline is not None

    def test_job_without_deadline(self, db: Session) -> None:
        student = _make_student(db)
        job = _make_job(db, student.id)
        assert job.deadline is None


# ---------------------------------------------------------------------------
# 5. JobFile
# ---------------------------------------------------------------------------

class TestJobFile:
    def test_job_file_creation(self, db: Session) -> None:
        from app.models.job import JobFile  # noqa: PLC0415

        student = _make_student(db)
        job = _make_job(db, student.id)
        jf = JobFile(
            id=uuid.uuid4(),
            job_id=job.id,
            file_name="test_file.pdf",
            file_url="https://example.com/test_file.pdf",
            file_size=1024,
            uploaded_by=student.id,
        )
        db.add(jf)
        db.commit()
        db.refresh(jf)
        assert jf.id is not None
        assert jf.file_name == "test_file.pdf"
        assert jf.file_size == 1024

    def test_job_file_associated_with_job(self, db: Session) -> None:
        from app.models.job import JobFile  # noqa: PLC0415

        student = _make_student(db)
        job = _make_job(db, student.id)
        jf = JobFile(
            id=uuid.uuid4(),
            job_id=job.id,
            file_name="attachment.docx",
            file_url="https://example.com/attachment.docx",
            file_size=2048,
            uploaded_by=student.id,
        )
        db.add(jf)
        db.commit()
        assert str(jf.job_id) == str(job.id)

    def test_job_file_repr(self, db: Session) -> None:
        from app.models.job import JobFile  # noqa: PLC0415

        student = _make_student(db)
        job = _make_job(db, student.id)
        jf = JobFile(
            id=uuid.uuid4(),
            job_id=job.id,
            file_name="report.pdf",
            file_url="https://example.com/report.pdf",
            file_size=512,
            uploaded_by=student.id,
        )
        db.add(jf)
        db.commit()
        assert "report.pdf" in repr(jf)

    def test_multiple_files_per_job(self, db: Session) -> None:
        from app.models.job import JobFile  # noqa: PLC0415

        student = _make_student(db)
        job = _make_job(db, student.id)
        for i in range(3):
            jf = JobFile(
                id=uuid.uuid4(),
                job_id=job.id,
                file_name=f"file_{i}.pdf",
                file_url=f"https://example.com/file_{i}.pdf",
                file_size=100 * (i + 1),
                uploaded_by=student.id,
            )
            db.add(jf)
        db.commit()
        from app.models.job import JobFile  # noqa: PLC0415, F811
        files = db.query(JobFile).filter(JobFile.job_id == job.id).all()
        assert len(files) == 3


# ---------------------------------------------------------------------------
# 6. Job __repr__
# ---------------------------------------------------------------------------

class TestJobRepr:
    def test_repr_includes_title(self, db: Session) -> None:
        student = _make_student(db)
        job = _make_job(db, student.id, title="Unique Title XYZ")
        assert "Unique Title XYZ" in repr(job)

    def test_repr_includes_status(self, db: Session) -> None:
        student = _make_student(db)
        job = _make_job(db, student.id, status="open")
        assert "open" in repr(job)


# ---------------------------------------------------------------------------
# 7. Job belongs to student (relationship)
# ---------------------------------------------------------------------------

class TestJobStudentRelationship:
    def test_job_student_relationship(self, db: Session) -> None:
        student = _make_student(db)
        job = _make_job(db, student.id)
        # Re-query to ensure relationship loads
        from app.models.job import Job  # noqa: PLC0415
        fetched = db.query(Job).filter(Job.id == job.id).first()
        assert fetched is not None
        assert str(fetched.student_id) == str(student.id)

    def test_proposed_price_stored_accurately(self, db: Session) -> None:
        student = _make_student(db)
        job = _make_job(db, student.id, proposed_price=999.99)
        assert abs(float(job.proposed_price) - 999.99) < 0.01
