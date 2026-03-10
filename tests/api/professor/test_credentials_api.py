"""
Tests for credential verification endpoints.

POST /api/v1/professor/credentials
GET  /api/v1/professor/credentials/pending
POST /api/v1/professor/credentials/{id}/action
GET  /api/v1/professor/credentials/researcher/{id}
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


CREDENTIAL_PAYLOAD = {
    "credential_type": "phd",
    "institution_name": "Massachusetts Institute of Technology",
    "field_of_study": "Computer Science",
    "year_obtained": 2015,
}


def _submit_credential(client, researcher_headers, payload=None):
    payload = payload or CREDENTIAL_PAYLOAD
    resp = client.post("/api/v1/professor/credentials", json=payload,
                       headers=researcher_headers)
    assert resp.status_code in (200, 201), f"Submit credential failed: {resp.text}"
    return resp.json()


def _get_researcher_id(client, researcher_headers):
    resp = client.get("/api/v1/auth/me", headers=researcher_headers)
    return resp.json()["data"]["id"]


# ---------------------------------------------------------------------------
# Submit credential (researcher)
# ---------------------------------------------------------------------------

def test_researcher_can_submit_credential(client, researcher_headers):
    """Researcher can submit a credential for verification."""
    resp = client.post("/api/v1/professor/credentials", json=CREDENTIAL_PAYLOAD,
                       headers=researcher_headers)
    assert resp.status_code in (200, 201)


def test_submitted_credential_has_pending_status(client, researcher_headers):
    """Submitted credential starts with 'pending' status."""
    cred = _submit_credential(client, researcher_headers)
    assert cred["status"] == "pending"


def test_credential_response_contains_required_fields(client, researcher_headers):
    """Credential response contains expected fields."""
    cred = _submit_credential(client, researcher_headers)
    assert "id" in cred
    assert cred["credential_type"] == CREDENTIAL_PAYLOAD["credential_type"]
    assert cred["institution_name"] == CREDENTIAL_PAYLOAD["institution_name"]


def test_student_cannot_submit_credential(client, student_headers):
    """Student cannot submit a credential (403)."""
    resp = client.post("/api/v1/professor/credentials", json=CREDENTIAL_PAYLOAD,
                       headers=student_headers)
    assert resp.status_code == 403


def test_professor_cannot_submit_credential(client, professor_headers):
    """Professor cannot submit credentials via researcher endpoint."""
    resp = client.post("/api/v1/professor/credentials", json=CREDENTIAL_PAYLOAD,
                       headers=professor_headers)
    assert resp.status_code == 403


def test_submit_credential_requires_auth(client):
    """Submitting a credential requires authentication."""
    resp = client.post("/api/v1/professor/credentials", json=CREDENTIAL_PAYLOAD)
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Get pending credentials (professor)
# ---------------------------------------------------------------------------

def test_approved_professor_can_view_pending_credentials(
    client, approved_professor_headers, researcher_headers
):
    """Approved professor can view pending credentials."""
    _submit_credential(client, researcher_headers)
    resp = client.get("/api/v1/professor/credentials/pending",
                      headers=approved_professor_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_pending_professor_cannot_view_pending_credentials(
    client, professor_headers, researcher_headers
):
    """Pending (non-approved) professor cannot view credentials (403)."""
    # Create professor profile (not approved)
    client.post("/api/v1/professor/profile",
                json={"bio": "Test prof", "title": "Dr.", "department": "CS",
                      "expertise_areas": [], "review_subjects": []},
                headers=professor_headers)
    _submit_credential(client, researcher_headers)
    resp = client.get("/api/v1/professor/credentials/pending", headers=professor_headers)
    assert resp.status_code == 403


def test_student_cannot_view_pending_credentials(client, student_headers):
    """Student cannot view pending credentials."""
    resp = client.get("/api/v1/professor/credentials/pending", headers=student_headers)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Action credential (approve/reject)
# ---------------------------------------------------------------------------

def test_approved_professor_can_verify_credential(
    client, approved_professor_headers, researcher_headers
):
    """Approved professor can verify a credential."""
    cred = _submit_credential(client, researcher_headers)
    resp = client.post(f"/api/v1/professor/credentials/{cred['id']}/action",
                       json={"action": "verify"},
                       headers=approved_professor_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "verified"


def test_approved_professor_can_reject_credential(
    client, approved_professor_headers, researcher_headers
):
    """Approved professor can reject a credential with a reason."""
    cred = _submit_credential(client, researcher_headers)
    resp = client.post(f"/api/v1/professor/credentials/{cred['id']}/action",
                       json={"action": "reject", "rejection_reason": "Document is not authentic."},
                       headers=approved_professor_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"


def test_reject_without_reason_returns_422(
    client, approved_professor_headers, researcher_headers
):
    """Rejecting a credential without a rejection_reason returns 422."""
    cred = _submit_credential(client, researcher_headers)
    resp = client.post(f"/api/v1/professor/credentials/{cred['id']}/action",
                       json={"action": "reject"},
                       headers=approved_professor_headers)
    assert resp.status_code == 422


def test_cannot_action_already_actioned_credential(
    client, approved_professor_headers, researcher_headers
):
    """Cannot action an already-actioned credential (409)."""
    cred = _submit_credential(client, researcher_headers)
    client.post(f"/api/v1/professor/credentials/{cred['id']}/action",
                json={"action": "verify"},
                headers=approved_professor_headers)
    resp = client.post(f"/api/v1/professor/credentials/{cred['id']}/action",
                       json={"action": "verify"},
                       headers=approved_professor_headers)
    assert resp.status_code == 409


def test_student_cannot_action_credential(client, student_headers, researcher_headers,
                                           approved_professor_headers):
    """Student cannot action a credential."""
    cred = _submit_credential(client, researcher_headers)
    resp = client.post(f"/api/v1/professor/credentials/{cred['id']}/action",
                       json={"action": "verify"},
                       headers=student_headers)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Get researcher credentials
# ---------------------------------------------------------------------------

def test_get_researcher_credentials(
    client, researcher_headers, approved_professor_headers
):
    """Can get credentials for a specific researcher."""
    _submit_credential(client, researcher_headers)
    researcher_id = _get_researcher_id(client, researcher_headers)
    resp = client.get(f"/api/v1/professor/credentials/researcher/{researcher_id}",
                      headers=approved_professor_headers)
    assert resp.status_code == 200
    creds = resp.json()
    assert isinstance(creds, list)
    assert len(creds) >= 1


def test_get_researcher_credentials_requires_auth(client, researcher_headers):
    """GET /credentials/researcher/{id} requires authentication."""
    researcher_id = _get_researcher_id(client, researcher_headers)
    resp = client.get(f"/api/v1/professor/credentials/researcher/{researcher_id}")
    assert resp.status_code == 401
