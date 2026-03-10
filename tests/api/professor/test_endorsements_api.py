"""
Tests for endorsement endpoints.

POST   /api/v1/professor/endorsements
GET    /api/v1/professor/endorsements/researcher/{id}
DELETE /api/v1/professor/endorsements/{id}
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient


def _get_researcher_id(client, researcher_headers):
    resp = client.get("/api/v1/auth/me", headers=researcher_headers)
    return resp.json()["data"]["id"]


def _create_endorsement(client, approved_professor_headers, researcher_id):
    resp = client.post("/api/v1/professor/endorsements",
                       json={
                           "researcher_id": researcher_id,
                           "subject_area": "Machine Learning",
                           "endorsement_text": "This researcher is highly skilled in ML.",
                       },
                       headers=approved_professor_headers)
    assert resp.status_code in (200, 201), f"Create endorsement failed: {resp.text}"
    return resp.json()


# ---------------------------------------------------------------------------
# Create endorsement
# ---------------------------------------------------------------------------

def test_approved_professor_can_endorse_researcher(
    client, approved_professor_headers, researcher_headers
):
    """Approved professor can endorse a researcher."""
    researcher_id = _get_researcher_id(client, researcher_headers)
    resp = client.post("/api/v1/professor/endorsements",
                       json={
                           "researcher_id": researcher_id,
                           "subject_area": "Machine Learning",
                           "endorsement_text": "Expert in ML.",
                       },
                       headers=approved_professor_headers)
    assert resp.status_code in (200, 201)


def test_endorsement_response_contains_required_fields(
    client, approved_professor_headers, researcher_headers
):
    """Endorsement response has required fields."""
    researcher_id = _get_researcher_id(client, researcher_headers)
    end = _create_endorsement(client, approved_professor_headers, researcher_id)
    assert "id" in end
    assert end["researcher_id"] == researcher_id
    assert end["subject_area"] == "Machine Learning"
    assert end["is_active"] is True


def test_pending_professor_cannot_endorse(client, professor_headers, researcher_headers):
    """Professor with pending profile cannot endorse (403)."""
    client.post("/api/v1/professor/profile",
                json={"bio": "Pending prof", "title": "Dr.", "department": "CS",
                      "expertise_areas": [], "review_subjects": []},
                headers=professor_headers)
    researcher_id = _get_researcher_id(client, researcher_headers)
    resp = client.post("/api/v1/professor/endorsements",
                       json={
                           "researcher_id": researcher_id,
                           "subject_area": "ML",
                           "endorsement_text": "Great.",
                       },
                       headers=professor_headers)
    assert resp.status_code == 403


def test_non_professor_cannot_endorse(client, student_headers, researcher_headers):
    """Non-professor cannot endorse (403)."""
    researcher_id = _get_researcher_id(client, researcher_headers)
    resp = client.post("/api/v1/professor/endorsements",
                       json={
                           "researcher_id": researcher_id,
                           "subject_area": "Chemistry",
                           "endorsement_text": "Good.",
                       },
                       headers=student_headers)
    assert resp.status_code == 403


def test_duplicate_endorsement_returns_409(
    client, approved_professor_headers, researcher_headers
):
    """Duplicate endorsement (same professor, researcher, subject) returns 409."""
    researcher_id = _get_researcher_id(client, researcher_headers)
    _create_endorsement(client, approved_professor_headers, researcher_id)
    resp = client.post("/api/v1/professor/endorsements",
                       json={
                           "researcher_id": researcher_id,
                           "subject_area": "Machine Learning",
                           "endorsement_text": "Duplicate.",
                       },
                       headers=approved_professor_headers)
    assert resp.status_code == 409


def test_create_endorsement_requires_auth(client, researcher_headers):
    """Creating endorsement requires authentication."""
    researcher_id = _get_researcher_id(client, researcher_headers)
    resp = client.post("/api/v1/professor/endorsements",
                       json={"researcher_id": researcher_id, "subject_area": "ML"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Get endorsements for researcher
# ---------------------------------------------------------------------------

def test_get_endorsements_for_researcher(
    client, approved_professor_headers, researcher_headers
):
    """Can get endorsements for a researcher."""
    researcher_id = _get_researcher_id(client, researcher_headers)
    _create_endorsement(client, approved_professor_headers, researcher_id)
    resp = client.get(f"/api/v1/professor/endorsements/researcher/{researcher_id}",
                      headers=approved_professor_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_get_endorsements_returns_empty_when_none(client, researcher_headers,
                                                    approved_professor_headers):
    """Returns empty list when researcher has no endorsements."""
    researcher_id = _get_researcher_id(client, researcher_headers)
    resp = client.get(f"/api/v1/professor/endorsements/researcher/{researcher_id}",
                      headers=approved_professor_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_endorsements_requires_auth(client, researcher_headers):
    """GET /endorsements/researcher/{id} requires authentication."""
    researcher_id = _get_researcher_id(client, researcher_headers)
    resp = client.get(f"/api/v1/professor/endorsements/researcher/{researcher_id}")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Revoke endorsement
# ---------------------------------------------------------------------------

def test_professor_can_revoke_endorsement(
    client, approved_professor_headers, researcher_headers
):
    """Professor can revoke (soft-delete) an endorsement."""
    researcher_id = _get_researcher_id(client, researcher_headers)
    end = _create_endorsement(client, approved_professor_headers, researcher_id)
    resp = client.delete(f"/api/v1/professor/endorsements/{end['id']}",
                         headers=approved_professor_headers)
    assert resp.status_code == 204


def test_revoked_endorsement_not_in_active_list(
    client, approved_professor_headers, researcher_headers
):
    """Revoked endorsement does not appear in active endorsements."""
    researcher_id = _get_researcher_id(client, researcher_headers)
    end = _create_endorsement(client, approved_professor_headers, researcher_id)
    client.delete(f"/api/v1/professor/endorsements/{end['id']}",
                  headers=approved_professor_headers)
    resp = client.get(f"/api/v1/professor/endorsements/researcher/{researcher_id}",
                      headers=approved_professor_headers)
    active = [e for e in resp.json() if e["is_active"]]
    assert len(active) == 0


def test_student_cannot_revoke_endorsement(
    client, approved_professor_headers, researcher_headers, student_headers
):
    """Student cannot revoke an endorsement."""
    researcher_id = _get_researcher_id(client, researcher_headers)
    end = _create_endorsement(client, approved_professor_headers, researcher_id)
    resp = client.delete(f"/api/v1/professor/endorsements/{end['id']}",
                         headers=student_headers)
    assert resp.status_code == 403


def test_different_professor_cannot_revoke_others_endorsement(
    client, approved_professor_headers, researcher_headers, db
):
    """A different professor cannot revoke another professor's endorsement."""
    from tests.conftest import auth_headers
    from app.models.user import User

    researcher_id = _get_researcher_id(client, researcher_headers)
    end = _create_endorsement(client, approved_professor_headers, researcher_id)

    # Create another approved professor
    email2 = f"prof2-{uuid.uuid4().hex[:8]}@test.com"
    password = "TestPassword123!"
    client.post("/api/v1/auth/register", json={
        "email": email2, "password": password,
        "first_name": "Prof2", "last_name": "User", "role": "student"
    })
    user2 = db.query(User).filter(User.email == email2).first()
    if user2:
        user2.role = "professor"
        db.commit()
    login2 = client.post("/api/v1/auth/login", json={"email": email2, "password": password})
    headers2 = {"Authorization": f"Bearer {login2.json()['data']['access_token']}"}

    # Create profile for professor 2
    client.post("/api/v1/professor/profile",
                json={"bio": "Second professor", "title": "Dr.", "department": "Math",
                      "expertise_areas": [], "review_subjects": []},
                headers=headers2)

    # Try to revoke first professor's endorsement
    resp = client.delete(f"/api/v1/professor/endorsements/{end['id']}",
                         headers=headers2)
    assert resp.status_code == 404
