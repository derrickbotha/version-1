"""
Tests for professor dispute arbitration endpoints.

GET  /api/v1/professor/disputes
POST /api/v1/professor/disputes/{id}/ruling
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient


RULING_REASONING = (
    "After careful review of all submitted evidence and the contract terms, "
    "I have determined that the researcher has fulfilled the agreed requirements "
    "and the work meets the academic standards. The student's complaints are not "
    "substantiated by the evidence provided in this dispute."
)


def _open_dispute(client, contract_id, headers):
    resp = client.post("/api/v1/disputes",
                       json={"contract_id": contract_id,
                             "reason": "Dispute for professor arbitration testing."},
                       headers=headers)
    assert resp.status_code in (200, 201)
    return resp.json()["data"]


def _submit_ruling(client, dispute_id, approved_professor_headers, ruling_data=None):
    if ruling_data is None:
        ruling_data = {
            "ruling": "full_release",
            "reasoning": RULING_REASONING,
            "evidence_reviewed": "Contract terms and submitted work.",
        }
    resp = client.post(f"/api/v1/professor/disputes/{dispute_id}/ruling",
                       json=ruling_data,
                       headers=approved_professor_headers)
    assert resp.status_code in (200, 201), f"Submit ruling failed: {resp.text}"
    return resp.json()


# ---------------------------------------------------------------------------
# Get assigned disputes
# ---------------------------------------------------------------------------

def test_get_assigned_disputes_returns_list(client, approved_professor_headers):
    """Approved professor can get their assigned disputes (may be empty)."""
    resp = client.get("/api/v1/professor/disputes", headers=approved_professor_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_get_assigned_disputes_requires_professor_role(client, student_headers):
    """Student cannot access professor disputes endpoint."""
    resp = client.get("/api/v1/professor/disputes", headers=student_headers)
    assert resp.status_code == 403


def test_pending_professor_cannot_get_disputes(client, professor_headers):
    """Pending professor cannot get assigned disputes."""
    client.post("/api/v1/professor/profile",
                json={"bio": "Pending", "title": "Dr.", "department": "CS",
                      "expertise_areas": [], "review_subjects": []},
                headers=professor_headers)
    resp = client.get("/api/v1/professor/disputes", headers=professor_headers)
    assert resp.status_code == 403


def test_get_disputes_requires_auth(client):
    """GET /professor/disputes requires authentication."""
    resp = client.get("/api/v1/professor/disputes")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Submit ruling
# ---------------------------------------------------------------------------

def test_professor_can_submit_full_release_ruling(
    client, approved_professor_headers, student_headers, started_contract
):
    """Professor can submit a full_release ruling on a dispute."""
    dispute = _open_dispute(client, started_contract["contract_id"], student_headers)
    resp = client.post(f"/api/v1/professor/disputes/{dispute['id']}/ruling",
                       json={
                           "ruling": "full_release",
                           "reasoning": RULING_REASONING,
                           "evidence_reviewed": "Submission and contract.",
                       },
                       headers=approved_professor_headers)
    assert resp.status_code in (200, 201)
    assert resp.json()["ruling"] == "full_release"


def test_professor_can_submit_full_refund_ruling(
    client, approved_professor_headers, student_headers, started_contract
):
    """Professor can submit a full_refund ruling."""
    dispute = _open_dispute(client, started_contract["contract_id"], student_headers)
    resp = client.post(f"/api/v1/professor/disputes/{dispute['id']}/ruling",
                       json={
                           "ruling": "full_refund",
                           "reasoning": RULING_REASONING,
                           "evidence_reviewed": "Submission and contract.",
                       },
                       headers=approved_professor_headers)
    assert resp.status_code in (200, 201)
    assert resp.json()["ruling"] == "full_refund"


def test_professor_can_submit_partial_release_ruling(
    client, approved_professor_headers, student_headers, started_contract
):
    """Professor can submit a partial_release ruling with release_percentage."""
    dispute = _open_dispute(client, started_contract["contract_id"], student_headers)
    resp = client.post(f"/api/v1/professor/disputes/{dispute['id']}/ruling",
                       json={
                           "ruling": "partial_release",
                           "release_percentage": 60.0,
                           "reasoning": RULING_REASONING,
                           "evidence_reviewed": "Contract and submitted work.",
                       },
                       headers=approved_professor_headers)
    assert resp.status_code in (200, 201)
    assert resp.json()["ruling"] == "partial_release"
    assert resp.json()["release_percentage"] == 60.0


def test_partial_release_without_percentage_returns_422(
    client, approved_professor_headers, student_headers, started_contract
):
    """partial_release ruling without release_percentage returns 422."""
    dispute = _open_dispute(client, started_contract["contract_id"], student_headers)
    resp = client.post(f"/api/v1/professor/disputes/{dispute['id']}/ruling",
                       json={
                           "ruling": "partial_release",
                           "reasoning": RULING_REASONING,
                       },
                       headers=approved_professor_headers)
    assert resp.status_code == 422


def test_professor_can_submit_revision_ruling(
    client, approved_professor_headers, student_headers, started_contract
):
    """Professor can submit a revision ruling."""
    dispute = _open_dispute(client, started_contract["contract_id"], student_headers)
    resp = client.post(f"/api/v1/professor/disputes/{dispute['id']}/ruling",
                       json={
                           "ruling": "revision",
                           "reasoning": RULING_REASONING,
                           "evidence_reviewed": "All submitted materials.",
                       },
                       headers=approved_professor_headers)
    assert resp.status_code in (200, 201)
    assert resp.json()["ruling"] == "revision"


def test_cannot_submit_ruling_on_already_ruled_dispute(
    client, approved_professor_headers, student_headers, started_contract
):
    """Cannot submit a second ruling on an already-ruled dispute (409)."""
    dispute = _open_dispute(client, started_contract["contract_id"], student_headers)
    _submit_ruling(client, dispute["id"], approved_professor_headers)
    resp = client.post(f"/api/v1/professor/disputes/{dispute['id']}/ruling",
                       json={
                           "ruling": "full_refund",
                           "reasoning": RULING_REASONING,
                       },
                       headers=approved_professor_headers)
    assert resp.status_code == 409


def test_pending_professor_cannot_submit_ruling(
    client, professor_headers, student_headers, started_contract
):
    """Pending professor cannot submit a ruling (403)."""
    client.post("/api/v1/professor/profile",
                json={"bio": "Pending", "title": "Dr.", "department": "CS",
                      "expertise_areas": [], "review_subjects": []},
                headers=professor_headers)
    dispute = _open_dispute(client, started_contract["contract_id"], student_headers)
    resp = client.post(f"/api/v1/professor/disputes/{dispute['id']}/ruling",
                       json={
                           "ruling": "full_release",
                           "reasoning": RULING_REASONING,
                       },
                       headers=professor_headers)
    assert resp.status_code == 403


def test_student_cannot_submit_ruling(client, student_headers, started_contract):
    """Student cannot submit a dispute ruling."""
    dispute = _open_dispute(client, started_contract["contract_id"], student_headers)
    resp = client.post(f"/api/v1/professor/disputes/{dispute['id']}/ruling",
                       json={
                           "ruling": "full_release",
                           "reasoning": RULING_REASONING,
                       },
                       headers=student_headers)
    assert resp.status_code == 403


def test_ruling_requires_auth(client, student_headers, started_contract):
    """POST /professor/disputes/{id}/ruling requires authentication."""
    dispute = _open_dispute(client, started_contract["contract_id"], student_headers)
    resp = client.post(f"/api/v1/professor/disputes/{dispute['id']}/ruling",
                       json={"ruling": "full_release", "reasoning": RULING_REASONING})
    assert resp.status_code == 401


def test_ruling_on_nonexistent_dispute_returns_404(
    client, approved_professor_headers
):
    """Ruling on non-existent dispute returns 404."""
    resp = client.post(f"/api/v1/professor/disputes/{uuid.uuid4()}/ruling",
                       json={"ruling": "full_release", "reasoning": RULING_REASONING},
                       headers=approved_professor_headers)
    assert resp.status_code == 404


def test_ruling_reasoning_too_short_returns_422(
    client, approved_professor_headers, student_headers, started_contract
):
    """Ruling reasoning must be at least 100 chars."""
    dispute = _open_dispute(client, started_contract["contract_id"], student_headers)
    resp = client.post(f"/api/v1/professor/disputes/{dispute['id']}/ruling",
                       json={
                           "ruling": "full_release",
                           "reasoning": "Too short.",
                       },
                       headers=approved_professor_headers)
    assert resp.status_code == 422
