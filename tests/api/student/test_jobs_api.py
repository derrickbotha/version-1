"""
Tests for the jobs API endpoints.

POST   /api/v1/jobs
GET    /api/v1/jobs
GET    /api/v1/jobs/mine
GET    /api/v1/jobs/{id}
PATCH  /api/v1/jobs/{id}
DELETE /api/v1/jobs/{id}
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

BASE = "/api/v1/jobs"

JOB_PAYLOAD = {
    "title": "Research on Machine Learning",
    "description": "I need comprehensive research on ML algorithms for my thesis.",
    "subject": "Computer Science",
    "academic_level": "Masters",
    "proposed_price": "150.00",
    "deadline": "2099-12-31T23:59:59Z",
}


def _create_job(client: TestClient, headers: dict) -> dict:
    resp = client.post(BASE, json=JOB_PAYLOAD, headers=headers)
    assert resp.status_code in (200, 201), f"Create job failed: {resp.text}"
    return resp.json()["data"]


# ---------------------------------------------------------------------------
# Creation tests
# ---------------------------------------------------------------------------

def test_create_job_as_student_returns_201(client, student_headers):
    """Student can create a job and gets 201."""
    resp = client.post(BASE, json=JOB_PAYLOAD, headers=student_headers)
    assert resp.status_code in (200, 201)


def test_create_job_returns_correct_fields(client, student_headers):
    """Created job contains all required fields."""
    resp = client.post(BASE, json=JOB_PAYLOAD, headers=student_headers)
    data = resp.json()["data"]
    assert "id" in data
    assert data["title"] == JOB_PAYLOAD["title"]
    assert data["description"] == JOB_PAYLOAD["description"]
    assert data["subject"] == JOB_PAYLOAD["subject"]
    assert data["academic_level"] == JOB_PAYLOAD["academic_level"]
    assert "proposed_price" in data
    assert "status" in data


def test_create_job_status_is_open(client, student_headers):
    """Created job has status open (jobs are created as open)."""
    data = _create_job(client, student_headers)
    assert data["status"] == "open"


def test_create_job_missing_title_returns_422(client, student_headers):
    """Missing required field (title) returns 422."""
    payload = {k: v for k, v in JOB_PAYLOAD.items() if k != "title"}
    resp = client.post(BASE, json=payload, headers=student_headers)
    assert resp.status_code == 422


def test_create_job_missing_description_returns_422(client, student_headers):
    """Missing description returns 422."""
    payload = {k: v for k, v in JOB_PAYLOAD.items() if k != "description"}
    resp = client.post(BASE, json=payload, headers=student_headers)
    assert resp.status_code == 422


def test_create_job_missing_price_returns_422(client, student_headers):
    """Missing proposed_price returns 422."""
    payload = {k: v for k, v in JOB_PAYLOAD.items() if k != "proposed_price"}
    resp = client.post(BASE, json=payload, headers=student_headers)
    assert resp.status_code == 422


def test_create_job_as_researcher_returns_403(client, researcher_headers):
    """Non-student (researcher) cannot create a job."""
    resp = client.post(BASE, json=JOB_PAYLOAD, headers=researcher_headers)
    assert resp.status_code == 403


def test_create_job_unauthenticated_returns_401(client):
    """Unauthenticated request to create a job returns 401."""
    resp = client.post(BASE, json=JOB_PAYLOAD)
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Listing tests
# ---------------------------------------------------------------------------

def test_list_jobs_returns_200(client, student_headers):
    """GET /jobs returns 200 with a list."""
    _create_job(client, student_headers)
    resp = client.get(BASE)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "items" in data
    assert "total" in data


def test_list_jobs_returns_open_jobs(client, student_headers):
    """List jobs returns the open job we just created."""
    _create_job(client, student_headers)
    resp = client.get(BASE)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] >= 1


def test_list_jobs_no_auth_required(client, student_headers):
    """GET /jobs requires no authentication."""
    _create_job(client, student_headers)
    resp = client.get(BASE)  # no headers
    assert resp.status_code == 200


def test_list_jobs_filter_by_subject(client, student_headers):
    """Filter by subject returns matching jobs only."""
    _create_job(client, student_headers)
    resp = client.get(BASE, params={"subject": "Computer Science"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    for item in data["items"]:
        assert "Computer Science" in item["subject"]


def test_list_jobs_filter_by_min_price(client, student_headers):
    """Filter by min_price excludes jobs below the threshold."""
    _create_job(client, student_headers)
    resp = client.get(BASE, params={"min_price": "200.00"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    for item in data["items"]:
        assert float(item["proposed_price"]) >= 200.00


def test_list_jobs_filter_by_max_price(client, student_headers):
    """Filter by max_price excludes jobs above the threshold."""
    _create_job(client, student_headers)
    resp = client.get(BASE, params={"max_price": "100.00"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    for item in data["items"]:
        assert float(item["proposed_price"]) <= 100.00


def test_list_jobs_pagination(client, student_headers):
    """Pagination parameters are respected."""
    # Create 3 jobs
    for _ in range(3):
        _create_job(client, student_headers)
    resp = client.get(BASE, params={"page": 1, "page_size": 2})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data["items"]) <= 2


# ---------------------------------------------------------------------------
# Mine endpoint
# ---------------------------------------------------------------------------

def test_get_my_jobs_returns_own_jobs(client, student_headers):
    """GET /jobs/mine returns the student's own jobs."""
    _create_job(client, student_headers)
    resp = client.get(f"{BASE}/mine", headers=student_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] >= 1


def test_get_my_jobs_requires_student_role(client, researcher_headers):
    """GET /jobs/mine requires student role."""
    resp = client.get(f"{BASE}/mine", headers=researcher_headers)
    assert resp.status_code == 403


def test_get_my_jobs_requires_auth(client):
    """GET /jobs/mine requires authentication."""
    resp = client.get(f"{BASE}/mine")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Get by ID tests
# ---------------------------------------------------------------------------

def test_get_job_by_id_returns_200(client, student_headers):
    """GET /jobs/{id} returns 200 for a valid job."""
    job = _create_job(client, student_headers)
    resp = client.get(f"{BASE}/{job['id']}", headers=student_headers)
    assert resp.status_code == 200


def test_get_job_by_id_returns_correct_data(client, student_headers):
    """GET /jobs/{id} returns the correct job data."""
    job = _create_job(client, student_headers)
    resp = client.get(f"{BASE}/{job['id']}", headers=student_headers)
    data = resp.json()["data"]
    assert data["id"] == job["id"]
    assert data["title"] == JOB_PAYLOAD["title"]


def test_get_job_by_nonexistent_id_returns_404(client, student_headers):
    """GET /jobs/{nonexistent_id} returns 404."""
    resp = client.get(f"{BASE}/{uuid.uuid4()}", headers=student_headers)
    assert resp.status_code == 404


def test_researcher_can_view_job_detail(client, student_headers, researcher_headers):
    """Researcher can view job details."""
    job = _create_job(client, student_headers)
    resp = client.get(f"{BASE}/{job['id']}", headers=researcher_headers)
    assert resp.status_code == 200


def test_job_response_contains_required_fields(client, student_headers):
    """Job response contains all required fields."""
    job = _create_job(client, student_headers)
    resp = client.get(f"{BASE}/{job['id']}", headers=student_headers)
    data = resp.json()["data"]
    required = ["id", "title", "description", "subject", "academic_level",
                "proposed_price", "status", "deadline"]
    for field in required:
        assert field in data, f"Missing field: {field}"


# ---------------------------------------------------------------------------
# Update tests
# ---------------------------------------------------------------------------

def test_student_can_update_own_job(client, student_headers):
    """Student can update their own open job."""
    job = _create_job(client, student_headers)
    resp = client.patch(
        f"{BASE}/{job['id']}",
        json={"title": "Updated Research Title"},
        headers=student_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["title"] == "Updated Research Title"


def test_student_cannot_update_another_students_job(client, student_headers, db):
    """Student cannot update another student's job."""
    from tests.conftest import auth_headers
    student2_headers = auth_headers(client, "student")
    job = _create_job(client, student_headers)
    resp = client.patch(
        f"{BASE}/{job['id']}",
        json={"title": "Hijacked Title"},
        headers=student2_headers,
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Delete tests
# ---------------------------------------------------------------------------

def test_student_can_delete_own_job(client, student_headers):
    """Student can delete (soft-delete) their own open job."""
    job = _create_job(client, student_headers)
    resp = client.delete(f"{BASE}/{job['id']}", headers=student_headers)
    assert resp.status_code == 200


def test_delete_job_unauthenticated_returns_401(client, student_headers):
    """Unauthenticated DELETE returns 401."""
    job = _create_job(client, student_headers)
    resp = client.delete(f"{BASE}/{job['id']}")
    assert resp.status_code == 401
