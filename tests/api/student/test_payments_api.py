"""
Tests for the payments API endpoints.

POST /api/v1/payments/escrow
POST /api/v1/payments/release
POST /api/v1/payments/refund
GET  /api/v1/payments/contract/{id}
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient


def _get_contract_status(client, contract_id, headers):
    resp = client.get(f"/api/v1/contracts/{contract_id}", headers=headers)
    return resp.json()["data"]["status"]


def _submit_and_approve(client, contract_id, researcher_headers, student_headers):
    """Helper: submit work, then approve it."""
    sub_resp = client.post("/api/v1/submissions",
                           json={"contract_id": contract_id,
                                 "submission_notes": "Work completed."},
                           headers=researcher_headers)
    sub_id = sub_resp.json()["data"]["id"]
    client.post(f"/api/v1/submissions/{sub_id}/approve", headers=student_headers)


# ---------------------------------------------------------------------------
# Escrow
# ---------------------------------------------------------------------------

def test_full_contract_has_escrowed_status(client, student_headers, full_contract):
    """full_contract fixture creates a contract with escrowed payment (contract in 'accepted' state)."""
    resp = client.get(f"/api/v1/contracts/{full_contract['contract_id']}", headers=student_headers)
    data = resp.json()["data"]
    # Contract status after escrow is still 'accepted' (not in_progress yet)
    assert data["status"] == "accepted"
    assert data["payment_escrowed"] is True


def test_escrow_reduces_wallet_balance(client, student_headers, full_contract):
    """Escrow reduces the student's wallet balance."""
    resp = client.get("/api/v1/payments/wallet", headers=student_headers)
    # The full_contract fixture deposited 500 and escrowed 180, so balance < 500
    assert float(resp.json()["data"]["balance"]) < 500.00


def test_cannot_escrow_same_contract_twice(client, student_headers, full_contract):
    """Cannot escrow the same contract twice (409)."""
    resp = client.post("/api/v1/payments/escrow",
                       json={
                           "contract_id": full_contract["contract_id"],
                           "payment_provider": "wallet",
                           "provider_reference": "dup-test",
                       },
                       headers=student_headers)
    assert resp.status_code == 409


def test_cannot_escrow_without_sufficient_funds(client, student_headers, researcher_headers):
    """Cannot escrow without sufficient wallet funds (402)."""
    # Create job+bid+accept without depositing
    job_resp = client.post("/api/v1/jobs", json={
        "title": "Funds Test Job",
        "description": "Testing insufficient funds for escrow.",
        "subject": "Biology",
        "academic_level": "Bachelors",
        "proposed_price": "500.00",
        "deadline": "2099-12-31T23:59:59Z",
    }, headers=student_headers)
    job_id = job_resp.json()["data"]["id"]

    bid_resp = client.post(f"/api/v1/jobs/{job_id}/bids",
                           json={"proposed_price": "500.00", "message": "I can do this."},
                           headers=researcher_headers)
    bid_id = bid_resp.json()["data"]["id"]

    accept_resp = client.post(f"/api/v1/bids/{bid_id}/accept", headers=student_headers)
    contract_id = accept_resp.json()["data"]["id"]

    # Try to escrow (no deposit, should fail with 402)
    resp = client.post("/api/v1/payments/escrow",
                       json={
                           "contract_id": contract_id,
                           "payment_provider": "wallet",
                           "provider_reference": "ref-broke",
                       },
                       headers=student_headers)
    assert resp.status_code == 402


def test_researcher_cannot_create_escrow(client, researcher_headers, full_contract):
    """Researcher cannot create escrow (student only)."""
    # Try to escrow another contract
    resp = client.post("/api/v1/payments/escrow",
                       json={
                           "contract_id": full_contract["contract_id"],
                           "payment_provider": "wallet",
                           "provider_reference": "ref-researcher",
                       },
                       headers=researcher_headers)
    assert resp.status_code == 403


def test_get_payment_by_contract_id(client, student_headers, full_contract):
    """Can get payment info by contract ID."""
    resp = client.get(f"/api/v1/payments/contract/{full_contract['contract_id']}",
                      headers=student_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "escrowed"


def test_get_payment_by_contract_requires_participant(client, full_contract, db):
    """Non-participant cannot get payment info."""
    from tests.conftest import auth_headers
    other_headers = auth_headers(client, "student")
    resp = client.get(f"/api/v1/payments/contract/{full_contract['contract_id']}",
                      headers=other_headers)
    assert resp.status_code in (403, 404)


# ---------------------------------------------------------------------------
# Release payment
# ---------------------------------------------------------------------------

def test_student_can_release_payment_after_approval(client, student_headers,
                                                      researcher_headers, started_contract):
    """Student can release payment after submission is approved."""
    _submit_and_approve(client, started_contract["contract_id"],
                        researcher_headers, student_headers)
    resp = client.post("/api/v1/payments/release",
                       json={"contract_id": started_contract["contract_id"]},
                       headers=student_headers)
    assert resp.status_code == 200


def test_release_payment_status_becomes_released(client, student_headers,
                                                   researcher_headers, started_contract):
    """Released payment has status 'released'."""
    _submit_and_approve(client, started_contract["contract_id"],
                        researcher_headers, student_headers)
    resp = client.post("/api/v1/payments/release",
                       json={"contract_id": started_contract["contract_id"]},
                       headers=student_headers)
    assert resp.json()["data"]["status"] == "released"


def test_release_credits_researcher_wallet(client, student_headers,
                                            researcher_headers, started_contract):
    """Releasing payment credits the researcher's wallet."""
    _submit_and_approve(client, started_contract["contract_id"],
                        researcher_headers, student_headers)
    client.post("/api/v1/payments/release",
                json={"contract_id": started_contract["contract_id"]},
                headers=student_headers)
    # Researcher wallet should now have funds
    resp = client.get("/api/v1/payments/wallet", headers=researcher_headers)
    assert resp.status_code == 200
    assert float(resp.json()["data"]["balance"]) > 0


def test_researcher_cannot_release_payment(client, researcher_headers, started_contract):
    """Researcher cannot release payment (student only)."""
    resp = client.post("/api/v1/payments/release",
                       json={"contract_id": started_contract["contract_id"]},
                       headers=researcher_headers)
    assert resp.status_code == 403


def test_release_requires_auth(client, started_contract):
    """Release payment requires authentication."""
    resp = client.post("/api/v1/payments/release",
                       json={"contract_id": started_contract["contract_id"]})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Refund payment
# ---------------------------------------------------------------------------

def test_student_can_request_refund(client, student_headers, researcher_headers, full_contract):
    """Student can request a refund on an escrowed payment."""
    # Start the contract first to have an in_progress one
    client.post(f"/api/v1/contracts/{full_contract['contract_id']}/start",
                headers=researcher_headers)
    resp = client.post("/api/v1/payments/refund",
                       json={"contract_id": full_contract["contract_id"],
                             "reason": "The researcher did not complete the work as agreed."},
                       headers=student_headers)
    assert resp.status_code == 200


def test_refund_payment_status_becomes_refunded(client, student_headers,
                                                  researcher_headers, full_contract):
    """Refunded payment has status 'refunded'."""
    client.post(f"/api/v1/contracts/{full_contract['contract_id']}/start",
                headers=researcher_headers)
    resp = client.post("/api/v1/payments/refund",
                       json={"contract_id": full_contract["contract_id"],
                             "reason": "Work not delivered."},
                       headers=student_headers)
    assert resp.json()["data"]["status"] == "refunded"


def test_researcher_cannot_refund_payment(client, researcher_headers, full_contract):
    """Researcher cannot refund payment (student or admin only)."""
    resp = client.post("/api/v1/payments/refund",
                       json={"contract_id": full_contract["contract_id"],
                             "reason": "Trying to refund myself."},
                       headers=researcher_headers)
    assert resp.status_code == 403


def test_refund_requires_auth(client, full_contract):
    """Refund requires authentication."""
    resp = client.post("/api/v1/payments/refund",
                       json={"contract_id": full_contract["contract_id"], "reason": "test"})
    assert resp.status_code == 401


def test_get_payment_by_contract_nonexistent_returns_404(client, student_headers):
    """GET /payments/contract/{nonexistent_id} returns 404."""
    resp = client.get(f"/api/v1/payments/contract/{uuid.uuid4()}", headers=student_headers)
    assert resp.status_code == 404
