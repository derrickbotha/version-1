"""
Tests for course assignment endpoints.

POST   /api/v1/professor/assignments
GET    /api/v1/professor/assignments
PATCH  /api/v1/professor/assignments/{id}
DELETE /api/v1/professor/assignments/{id}
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient


ASSIGNMENT_PAYLOAD = {
    "title": "Introduction to Quantum Computing Research",
    "description": "Students must research the fundamentals of quantum computing "
                   "and provide a comprehensive literature review.",
    "subject": "Physics",
    "academic_level": "Masters",
    "rubric": "Introduction 20%, Literature Review 40%, Analysis 30%, Conclusion 10%",
    "review_required": True,
    "suggested_price": 150.00,
    "deadline_hours": 72,
}


def _create_assignment(client, approved_professor_headers, payload=None):
    payload = payload or ASSIGNMENT_PAYLOAD
    resp = client.post("/api/v1/professor/assignments", json=payload,
                       headers=approved_professor_headers)
    assert resp.status_code in (200, 201), f"Create assignment failed: {resp.text}"
    return resp.json()


# ---------------------------------------------------------------------------
# Create assignment
# ---------------------------------------------------------------------------

def test_approved_professor_can_create_assignment(client, approved_professor_headers):
    """Approved professor can create an assignment."""
    resp = client.post("/api/v1/professor/assignments", json=ASSIGNMENT_PAYLOAD,
                       headers=approved_professor_headers)
    assert resp.status_code in (200, 201)


def test_assignment_response_contains_required_fields(client, approved_professor_headers):
    """Assignment response contains expected fields."""
    asn = _create_assignment(client, approved_professor_headers)
    assert "id" in asn
    assert asn["title"] == ASSIGNMENT_PAYLOAD["title"]
    assert asn["subject"] == ASSIGNMENT_PAYLOAD["subject"]
    assert asn["is_active"] is True


def test_pending_professor_cannot_create_assignment(client, professor_headers):
    """Professor with pending profile cannot create an assignment (403)."""
    client.post("/api/v1/professor/profile",
                json={"bio": "Pending", "title": "Dr.", "department": "CS",
                      "expertise_areas": [], "review_subjects": []},
                headers=professor_headers)
    resp = client.post("/api/v1/professor/assignments", json=ASSIGNMENT_PAYLOAD,
                       headers=professor_headers)
    assert resp.status_code == 403


def test_student_cannot_create_assignment(client, student_headers):
    """Student cannot create an assignment (403)."""
    resp = client.post("/api/v1/professor/assignments", json=ASSIGNMENT_PAYLOAD,
                       headers=student_headers)
    assert resp.status_code == 403


def test_researcher_cannot_create_assignment(client, researcher_headers):
    """Researcher cannot create an assignment (403)."""
    resp = client.post("/api/v1/professor/assignments", json=ASSIGNMENT_PAYLOAD,
                       headers=researcher_headers)
    assert resp.status_code == 403


def test_create_assignment_requires_auth(client):
    """Creating assignment requires authentication."""
    resp = client.post("/api/v1/professor/assignments", json=ASSIGNMENT_PAYLOAD)
    assert resp.status_code == 401


def test_assignment_title_too_short_returns_422(client, approved_professor_headers):
    """Assignment title must be at least 5 chars."""
    payload = {**ASSIGNMENT_PAYLOAD, "title": "Hi"}
    resp = client.post("/api/v1/professor/assignments", json=payload,
                       headers=approved_professor_headers)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# List assignments
# ---------------------------------------------------------------------------

def test_professor_can_list_own_assignments(client, approved_professor_headers):
    """Professor can list their own assignments."""
    _create_assignment(client, approved_professor_headers)
    resp = client.get("/api/v1/professor/assignments", headers=approved_professor_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_list_assignments_returns_empty_when_none(client, approved_professor_headers):
    """List returns empty list when no assignments exist."""
    resp = client.get("/api/v1/professor/assignments", headers=approved_professor_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_student_cannot_list_professor_assignments(client, student_headers):
    """Student cannot list assignments (403)."""
    resp = client.get("/api/v1/professor/assignments", headers=student_headers)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Update assignment
# ---------------------------------------------------------------------------

def test_professor_can_update_assignment(client, approved_professor_headers):
    """Professor can update an assignment."""
    asn = _create_assignment(client, approved_professor_headers)
    resp = client.patch(f"/api/v1/professor/assignments/{asn['id']}",
                        json={"suggested_price": 200.0},
                        headers=approved_professor_headers)
    assert resp.status_code == 200
    assert resp.json()["suggested_price"] == 200.0


def test_update_nonexistent_assignment_returns_404(client, approved_professor_headers):
    """Updating non-existent assignment returns 404."""
    resp = client.patch(f"/api/v1/professor/assignments/{uuid.uuid4()}",
                        json={"suggested_price": 200.0},
                        headers=approved_professor_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Delete assignment (soft delete)
# ---------------------------------------------------------------------------

def test_professor_can_soft_delete_assignment(client, approved_professor_headers):
    """Professor can soft-delete an assignment."""
    asn = _create_assignment(client, approved_professor_headers)
    resp = client.delete(f"/api/v1/professor/assignments/{asn['id']}",
                         headers=approved_professor_headers)
    assert resp.status_code == 204


def test_student_cannot_delete_assignment(client, student_headers, approved_professor_headers):
    """Student cannot delete an assignment."""
    asn = _create_assignment(client, approved_professor_headers)
    resp = client.delete(f"/api/v1/professor/assignments/{asn['id']}",
                         headers=student_headers)
    assert resp.status_code == 403


def test_deleted_assignment_is_inactive(client, approved_professor_headers):
    """Soft-deleted assignment has is_active=False."""
    asn = _create_assignment(client, approved_professor_headers)
    client.delete(f"/api/v1/professor/assignments/{asn['id']}",
                  headers=approved_professor_headers)
    resp = client.get("/api/v1/professor/assignments", headers=approved_professor_headers)
    found = [a for a in resp.json() if a["id"] == asn["id"]]
    if found:
        assert found[0]["is_active"] is False
