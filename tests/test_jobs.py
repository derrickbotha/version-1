"""
Tests for the job endpoints:
  POST   /api/v1/jobs
  GET    /api/v1/jobs
  GET    /api/v1/jobs/{id}
  PATCH  /api/v1/jobs/{id}
  DELETE /api/v1/jobs/{id}
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

JOB_PAYLOAD = {
    "title": "Quantitative Research Analysis",
    "description": "Need help with quantitative methods for my thesis research project.",
    "subject": "Statistics",
    "academic_level": "Masters",
    "proposed_price": "200.00",
    "deadline": "2099-06-30T12:00:00Z",
}


def _create_job(client: TestClient, headers: dict) -> dict:
    resp = client.post("/api/v1/jobs", json=JOB_PAYLOAD, headers=headers)
    assert resp.status_code in (200, 201), f"Unexpected status {resp.status_code}: {resp.text}"
    return resp.json()["data"]


# ---------------------------------------------------------------------------
# Creation
# ---------------------------------------------------------------------------

def test_create_job_as_student(client: TestClient, student_headers: dict) -> None:
    """A student can create a job and receives it back in the response."""
    resp = client.post("/api/v1/jobs", json=JOB_PAYLOAD, headers=student_headers)
    assert resp.status_code in (200, 201)
    data = resp.json()["data"]
    assert data["title"] == JOB_PAYLOAD["title"]
    assert "id" in data
    assert data["status"] in ("draft", "open")


def test_create_job_as_researcher(client: TestClient, researcher_headers: dict) -> None:
    """A researcher is not allowed to create jobs — expect 403."""
    resp = client.post("/api/v1/jobs", json=JOB_PAYLOAD, headers=researcher_headers)
    assert resp.status_code == 403


def test_create_job_unauthenticated(client: TestClient) -> None:
    """Unauthenticated requests to create a job return 401."""
    resp = client.post("/api/v1/jobs", json=JOB_PAYLOAD)
    assert resp.status_code == 401


def test_create_job_missing_fields(client: TestClient, student_headers: dict) -> None:
    """Missing required fields return 422."""
    resp = client.post(
        "/api/v1/jobs",
        json={"title": "Too short"},
        headers=student_headers,
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------

def test_list_jobs_public(client: TestClient, sample_job: dict) -> None:
    """GET /api/v1/jobs requires no authentication and returns a list."""
    resp = client.get("/api/v1/jobs")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    data = body["data"]
    assert "items" in data
    assert isinstance(data["items"], list)
    assert data["total"] >= 0


def test_list_jobs_pagination(client: TestClient, student_headers: dict) -> None:
    """Pagination query parameters are respected."""
    resp = client.get("/api/v1/jobs?page=1&page_size=5")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["page"] == 1
    assert data["page_size"] == 5


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------

def test_get_job_detail(client: TestClient, student_headers: dict, sample_job: dict) -> None:
    """GET /api/v1/jobs/{id} returns the job when authenticated."""
    job_id = sample_job["id"]
    resp = client.get(f"/api/v1/jobs/{job_id}", headers=student_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == job_id


def test_get_job_not_found(client: TestClient, student_headers: dict) -> None:
    """GET /api/v1/jobs/<non-existent-id> returns 404."""
    resp = client.get(f"/api/v1/jobs/{uuid.uuid4()}", headers=student_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

def test_update_job_owner(client: TestClient, student_headers: dict, sample_job: dict) -> None:
    """The owning student can update a job's fields."""
    job_id = sample_job["id"]
    resp = client.patch(
        f"/api/v1/jobs/{job_id}",
        json={"title": "Updated Research Title for Test"},
        headers=student_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["title"] == "Updated Research Title for Test"


def test_update_job_non_owner(
    client: TestClient,
    student_headers: dict,
    sample_job: dict,
) -> None:
    """
    A second student (non-owner) cannot update the job — expect 403.

    We create a second student to simulate the non-owner scenario.
    """
    import uuid as _uuid  # noqa: PLC0415

    email2 = f"student2-{_uuid.uuid4().hex[:6]}@test.com"
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email2,
            "password": "AnotherPass123!",
            "first_name": "Other",
            "last_name": "Student",
            "role": "student",
        },
    )
    login2 = client.post(
        "/api/v1/auth/login",
        json={"email": email2, "password": "AnotherPass123!"},
    )
    token2 = login2.json()["data"]["access_token"]
    other_headers = {"Authorization": f"Bearer {token2}"}

    job_id = sample_job["id"]
    resp = client.patch(
        f"/api/v1/jobs/{job_id}",
        json={"title": "Hacked Title Attempt by Non-Owner"},
        headers=other_headers,
    )
    assert resp.status_code == 403


def test_update_job_as_researcher(
    client: TestClient,
    researcher_headers: dict,
    sample_job: dict,
) -> None:
    """A researcher cannot update any job — expect 403."""
    resp = client.patch(
        f"/api/v1/jobs/{sample_job['id']}",
        json={"title": "Researcher Trying to Edit"},
        headers=researcher_headers,
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Deletion
# ---------------------------------------------------------------------------

def test_delete_job(client: TestClient, student_headers: dict, sample_job: dict) -> None:
    """The owning student can delete their own job."""
    job_id = sample_job["id"]
    resp = client.delete(f"/api/v1/jobs/{job_id}", headers=student_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

def test_filter_jobs_by_status(client: TestClient, sample_job: dict) -> None:
    """GET /api/v1/jobs?status=open returns only open jobs."""
    resp = client.get("/api/v1/jobs?status=open")
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    for item in items:
        assert item["status"] == "open"


def test_filter_jobs_by_subject(client: TestClient, student_headers: dict) -> None:
    """GET /api/v1/jobs?subject=Statistics filters by subject (partial match)."""
    # Create a job we know exists with subject=Statistics
    client.post("/api/v1/jobs", json=JOB_PAYLOAD, headers=student_headers)

    resp = client.get("/api/v1/jobs?subject=Statistics")
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    for item in items:
        assert "statistics" in item["subject"].lower()
