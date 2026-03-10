"""
Tests for professor profile endpoints.

POST  /api/v1/professor/profile
GET   /api/v1/professor/profile
PATCH /api/v1/professor/profile
GET   /api/v1/professor/institutions
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


PROFILE_PAYLOAD = {
    "bio": "Professor of Computer Science with 15 years of research experience.",
    "title": "Dr.",
    "department": "Computer Science",
    "expertise_areas": ["Machine Learning", "Algorithms"],
    "review_subjects": ["Computer Science", "Mathematics"],
}


# ---------------------------------------------------------------------------
# Create profile
# ---------------------------------------------------------------------------

def test_professor_can_create_profile(client, professor_headers):
    """Professor can create a profile, returns 201."""
    resp = client.post("/api/v1/professor/profile", json=PROFILE_PAYLOAD,
                       headers=professor_headers)
    assert resp.status_code in (200, 201)


def test_create_profile_returns_correct_data(client, professor_headers):
    """Created profile response contains expected fields."""
    resp = client.post("/api/v1/professor/profile", json=PROFILE_PAYLOAD,
                       headers=professor_headers)
    data = resp.json()
    assert "id" in data
    assert data["bio"] == PROFILE_PAYLOAD["bio"]
    assert data["title"] == PROFILE_PAYLOAD["title"]
    assert data["department"] == PROFILE_PAYLOAD["department"]


def test_profile_starts_as_pending(client, professor_headers):
    """Newly created professor profile starts with 'pending' status."""
    resp = client.post("/api/v1/professor/profile", json=PROFILE_PAYLOAD,
                       headers=professor_headers)
    assert resp.json()["status"] == "pending"


def test_student_cannot_create_professor_profile(client, student_headers):
    """Student cannot create a professor profile (403)."""
    resp = client.post("/api/v1/professor/profile", json=PROFILE_PAYLOAD,
                       headers=student_headers)
    assert resp.status_code == 403


def test_researcher_cannot_create_professor_profile(client, researcher_headers):
    """Researcher cannot create a professor profile (403)."""
    resp = client.post("/api/v1/professor/profile", json=PROFILE_PAYLOAD,
                       headers=researcher_headers)
    assert resp.status_code == 403


def test_cannot_create_duplicate_profile(client, professor_headers):
    """Cannot create a second professor profile (409)."""
    client.post("/api/v1/professor/profile", json=PROFILE_PAYLOAD, headers=professor_headers)
    resp = client.post("/api/v1/professor/profile", json=PROFILE_PAYLOAD,
                       headers=professor_headers)
    assert resp.status_code == 409


def test_create_profile_requires_auth(client):
    """Creating a profile requires authentication."""
    resp = client.post("/api/v1/professor/profile", json=PROFILE_PAYLOAD)
    assert resp.status_code == 401


def test_create_profile_minimal_fields(client, professor_headers):
    """Can create a profile with minimal fields (all optional except role)."""
    resp = client.post("/api/v1/professor/profile", json={},
                       headers=professor_headers)
    assert resp.status_code in (200, 201)


# ---------------------------------------------------------------------------
# Get profile
# ---------------------------------------------------------------------------

def test_professor_can_get_own_profile(client, professor_headers):
    """Professor can get their own profile."""
    client.post("/api/v1/professor/profile", json=PROFILE_PAYLOAD, headers=professor_headers)
    resp = client.get("/api/v1/professor/profile", headers=professor_headers)
    assert resp.status_code == 200


def test_get_profile_without_creating_returns_404(client, professor_headers):
    """GET /professor/profile returns 404 if no profile exists."""
    resp = client.get("/api/v1/professor/profile", headers=professor_headers)
    assert resp.status_code == 404


def test_get_profile_requires_professor_role(client, student_headers):
    """GET /professor/profile requires professor role."""
    resp = client.get("/api/v1/professor/profile", headers=student_headers)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Update profile
# ---------------------------------------------------------------------------

def test_professor_can_update_profile(client, professor_headers):
    """Professor can update their profile."""
    client.post("/api/v1/professor/profile", json=PROFILE_PAYLOAD, headers=professor_headers)
    resp = client.patch("/api/v1/professor/profile",
                        json={"bio": "Updated bio with more detail."},
                        headers=professor_headers)
    assert resp.status_code == 200
    assert resp.json()["bio"] == "Updated bio with more detail."


def test_update_profile_requires_professor_role(client, student_headers):
    """PATCH /professor/profile requires professor role."""
    resp = client.patch("/api/v1/professor/profile",
                        json={"bio": "Attempted update."},
                        headers=student_headers)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Approved professor profile
# ---------------------------------------------------------------------------

def test_approved_professor_profile_has_approved_status(client, approved_professor_headers):
    """Approved professor profile has status 'approved'."""
    resp = client.get("/api/v1/professor/profile", headers=approved_professor_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"


# ---------------------------------------------------------------------------
# Institutions
# ---------------------------------------------------------------------------

def test_list_institutions_requires_auth(client, professor_headers):
    """GET /professor/institutions requires authentication."""
    resp = client.get("/api/v1/professor/institutions", headers=professor_headers)
    assert resp.status_code == 200  # returns empty list if no institutions


def test_list_institutions_unauthenticated_returns_401(client):
    """GET /professor/institutions requires authentication."""
    resp = client.get("/api/v1/professor/institutions")
    assert resp.status_code == 401


def test_list_institutions_returns_list(client, professor_headers):
    """List institutions returns a list (may be empty)."""
    resp = client.get("/api/v1/professor/institutions", headers=professor_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
