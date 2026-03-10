"""
Tests for the disputes API endpoints.

POST /api/v1/disputes
GET  /api/v1/disputes/mine
GET  /api/v1/disputes/{id}
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient


DISPUTE_REASON = "The researcher did not complete the work as specified in the contract requirements."


def _open_dispute(client, contract_id, headers):
    resp = client.post("/api/v1/disputes",
                       json={"contract_id": contract_id, "reason": DISPUTE_REASON},
                       headers=headers)
    assert resp.status_code in (200, 201), f"Open dispute failed: {resp.text}"
    return resp.json()["data"]


# ---------------------------------------------------------------------------
# Open dispute
# ---------------------------------------------------------------------------

def test_student_can_open_dispute_on_started_contract(client, student_headers, started_contract):
    """Student can open a dispute on an in_progress contract."""
    resp = client.post("/api/v1/disputes",
                       json={"contract_id": started_contract["contract_id"],
                             "reason": DISPUTE_REASON},
                       headers=student_headers)
    assert resp.status_code in (200, 201)


def test_researcher_can_open_dispute(client, researcher_headers, started_contract):
    """Researcher can also open a dispute."""
    resp = client.post("/api/v1/disputes",
                       json={"contract_id": started_contract["contract_id"],
                             "reason": DISPUTE_REASON},
                       headers=researcher_headers)
    assert resp.status_code in (200, 201)


def test_dispute_response_contains_required_fields(client, student_headers, started_contract):
    """Dispute response contains required fields."""
    dispute = _open_dispute(client, started_contract["contract_id"], student_headers)
    assert "id" in dispute
    assert dispute["contract_id"] == started_contract["contract_id"]
    assert dispute["status"] == "open"
    assert dispute["reason"] == DISPUTE_REASON


def test_dispute_requires_reason(client, student_headers, started_contract):
    """Cannot open a dispute without a reason (422)."""
    resp = client.post("/api/v1/disputes",
                       json={"contract_id": started_contract["contract_id"]},
                       headers=student_headers)
    assert resp.status_code == 422


def test_cannot_dispute_completed_contract(client, student_headers, researcher_headers,
                                            started_contract):
    """Cannot open a dispute on a completed contract (400)."""
    # Submit and approve to complete the contract
    sub_resp = client.post("/api/v1/submissions",
                           json={"contract_id": started_contract["contract_id"],
                                 "submission_notes": "Work done."},
                           headers=researcher_headers)
    sub_id = sub_resp.json()["data"]["id"]
    client.post(f"/api/v1/submissions/{sub_id}/approve", headers=student_headers)
    # Now try to dispute
    resp = client.post("/api/v1/disputes",
                       json={"contract_id": started_contract["contract_id"],
                             "reason": DISPUTE_REASON},
                       headers=student_headers)
    assert resp.status_code == 400


def test_cannot_dispute_cancelled_contract(client, student_headers, researcher_headers,
                                            full_contract):
    """Cannot open a dispute on a cancelled contract (400)."""
    # Start then refund to cancel
    client.post(f"/api/v1/contracts/{full_contract['contract_id']}/start",
                headers=researcher_headers)
    client.post("/api/v1/payments/refund",
                json={"contract_id": full_contract["contract_id"], "reason": "Cancel test."},
                headers=student_headers)
    resp = client.post("/api/v1/disputes",
                       json={"contract_id": full_contract["contract_id"],
                             "reason": DISPUTE_REASON},
                       headers=student_headers)
    assert resp.status_code == 400


def test_cannot_double_dispute_same_contract(client, student_headers, researcher_headers,
                                              started_contract):
    """Cannot open two disputes on the same contract."""
    _open_dispute(client, started_contract["contract_id"], student_headers)
    resp = client.post("/api/v1/disputes",
                       json={"contract_id": started_contract["contract_id"],
                             "reason": "Second dispute attempt."},
                       headers=researcher_headers)
    assert resp.status_code == 400


def test_open_dispute_on_nonexistent_contract_returns_404(client, student_headers):
    """Opening dispute on non-existent contract returns 404."""
    resp = client.post("/api/v1/disputes",
                       json={"contract_id": str(uuid.uuid4()), "reason": DISPUTE_REASON},
                       headers=student_headers)
    assert resp.status_code == 404


def test_unauthenticated_cannot_open_dispute(client, started_contract):
    """Unauthenticated cannot open dispute."""
    resp = client.post("/api/v1/disputes",
                       json={"contract_id": started_contract["contract_id"],
                             "reason": DISPUTE_REASON})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Get own disputes
# ---------------------------------------------------------------------------

def test_get_own_disputes(client, student_headers, started_contract):
    """GET /disputes/mine returns disputes opened by the user."""
    _open_dispute(client, started_contract["contract_id"], student_headers)
    resp = client.get("/api/v1/disputes/mine", headers=student_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] >= 1


def test_get_own_disputes_returns_empty_when_none(client, student_headers):
    """GET /disputes/mine returns empty list when no disputes exist."""
    resp = client.get("/api/v1/disputes/mine", headers=student_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] == 0


def test_get_own_disputes_requires_auth(client):
    """GET /disputes/mine requires authentication."""
    resp = client.get("/api/v1/disputes/mine")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Get dispute by ID
# ---------------------------------------------------------------------------

def test_get_dispute_by_id(client, student_headers, started_contract):
    """Student can get their own dispute by ID."""
    dispute = _open_dispute(client, started_contract["contract_id"], student_headers)
    resp = client.get(f"/api/v1/disputes/{dispute['id']}", headers=student_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == dispute["id"]


def test_get_dispute_by_id_for_researcher(client, researcher_headers, started_contract):
    """Researcher can get a dispute for a contract they're part of."""
    dispute = _open_dispute(client, started_contract["contract_id"], researcher_headers)
    resp = client.get(f"/api/v1/disputes/{dispute['id']}", headers=researcher_headers)
    assert resp.status_code == 200


def test_non_participant_cannot_get_dispute(client, student_headers, started_contract, db):
    """Non-participant cannot access a dispute."""
    from tests.conftest import auth_headers
    other_headers = auth_headers(client, "student")
    dispute = _open_dispute(client, started_contract["contract_id"], student_headers)
    resp = client.get(f"/api/v1/disputes/{dispute['id']}", headers=other_headers)
    assert resp.status_code == 403


def test_get_nonexistent_dispute_returns_404(client, student_headers):
    """GET /disputes/{nonexistent_id} returns 404."""
    resp = client.get(f"/api/v1/disputes/{uuid.uuid4()}", headers=student_headers)
    assert resp.status_code == 404
