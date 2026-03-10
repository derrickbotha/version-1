"""
Tests for the contracts API endpoints.

GET  /api/v1/contracts
GET  /api/v1/contracts/{id}
POST /api/v1/contracts/{id}/start

Notes:
- full_contract fixture: contract is in 'escrowed' status (payment escrowed, not yet started)
  Actually the contract status after escrow is still 'accepted'. The contract transitions
  to 'in_progress' after researcher calls start.
- started_contract fixture: contract is in 'in_progress' status
- start_contract requires: contract.status == 'accepted' AND an escrowed payment exists
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# List contracts
# ---------------------------------------------------------------------------

def test_student_can_list_own_contracts(client, student_headers, full_contract):
    """Student can list their own contracts."""
    resp = client.get("/api/v1/contracts", headers=student_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "items" in data
    assert data["total"] >= 1


def test_researcher_can_list_own_contracts(client, researcher_headers, full_contract):
    """Researcher can list their own contracts."""
    resp = client.get("/api/v1/contracts", headers=researcher_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] >= 1


def test_list_contracts_requires_auth(client):
    """GET /contracts requires authentication."""
    resp = client.get("/api/v1/contracts")
    assert resp.status_code == 401


def test_admin_can_list_all_contracts(client, admin_headers, full_contract):
    """Admin can list all contracts."""
    resp = client.get("/api/v1/contracts", headers=admin_headers)
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Get contract by ID
# ---------------------------------------------------------------------------

def test_get_contract_by_id_returns_200(client, student_headers, full_contract):
    """Student can fetch their contract by ID."""
    resp = client.get(f"/api/v1/contracts/{full_contract['contract_id']}", headers=student_headers)
    assert resp.status_code == 200


def test_get_contract_by_id_contains_correct_data(client, student_headers, full_contract):
    """Contract detail contains required fields."""
    resp = client.get(f"/api/v1/contracts/{full_contract['contract_id']}", headers=student_headers)
    data = resp.json()["data"]
    assert data["id"] == full_contract["contract_id"]
    assert "agreed_price" in data
    assert "status" in data
    assert "job_id" in data


def test_get_contract_includes_job_info(client, student_headers, full_contract):
    """Contract detail includes job info."""
    resp = client.get(f"/api/v1/contracts/{full_contract['contract_id']}", headers=student_headers)
    data = resp.json()["data"]
    assert data.get("job") is not None or "job_id" in data


def test_get_contract_includes_agreed_price(client, student_headers, full_contract):
    """Contract detail includes agreed_price."""
    resp = client.get(f"/api/v1/contracts/{full_contract['contract_id']}", headers=student_headers)
    data = resp.json()["data"]
    assert "agreed_price" in data
    assert float(data["agreed_price"]) > 0


def test_researcher_can_get_contract_by_id(client, researcher_headers, full_contract):
    """Researcher can fetch their contract by ID."""
    resp = client.get(f"/api/v1/contracts/{full_contract['contract_id']}", headers=researcher_headers)
    assert resp.status_code == 200


def test_non_participant_cannot_get_contract(client, full_contract, db):
    """Non-participant cannot access a contract."""
    from tests.conftest import auth_headers
    other_student_headers = auth_headers(client, "student")
    resp = client.get(f"/api/v1/contracts/{full_contract['contract_id']}", headers=other_student_headers)
    assert resp.status_code == 403


def test_get_nonexistent_contract_returns_404(client, student_headers):
    """GET /contracts/{nonexistent_id} returns 404."""
    resp = client.get(f"/api/v1/contracts/{uuid.uuid4()}", headers=student_headers)
    assert resp.status_code == 404


def test_get_contract_requires_auth(client, full_contract):
    """GET /contracts/{id} requires authentication."""
    resp = client.get(f"/api/v1/contracts/{full_contract['contract_id']}")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Start contract
# ---------------------------------------------------------------------------

def test_researcher_can_start_contract(client, researcher_headers, full_contract):
    """Researcher can start a contract that is in 'accepted' status with escrowed payment."""
    resp = client.post(f"/api/v1/contracts/{full_contract['contract_id']}/start",
                       headers=researcher_headers)
    assert resp.status_code == 200


def test_start_contract_transitions_to_in_progress(client, researcher_headers, full_contract):
    """Starting a contract transitions status to in_progress."""
    resp = client.post(f"/api/v1/contracts/{full_contract['contract_id']}/start",
                       headers=researcher_headers)
    data = resp.json()["data"]
    assert data["status"] == "in_progress"


def test_student_cannot_start_contract(client, student_headers, full_contract):
    """Student cannot start a contract (researcher only)."""
    resp = client.post(f"/api/v1/contracts/{full_contract['contract_id']}/start",
                       headers=student_headers)
    assert resp.status_code == 403


def test_start_contract_requires_escrowed_payment(client, student_headers, researcher_headers):
    """Start contract without escrowed payment returns 402."""
    # Create job and accept bid but do NOT escrow
    job_resp = client.post("/api/v1/jobs", json={
        "title": "No Escrow Job",
        "description": "This job will not have payment escrowed.",
        "subject": "Chemistry",
        "academic_level": "Bachelors",
        "proposed_price": "100.00",
        "deadline": "2099-12-31T23:59:59Z",
    }, headers=student_headers)
    job_id = job_resp.json()["data"]["id"]

    bid_resp = client.post(f"/api/v1/jobs/{job_id}/bids",
                           json={"proposed_price": "90.00", "message": "I can do this."},
                           headers=researcher_headers)
    bid_id = bid_resp.json()["data"]["id"]

    accept_resp = client.post(f"/api/v1/bids/{bid_id}/accept", headers=student_headers)
    contract_id = accept_resp.json()["data"]["id"]

    # Try to start without escrow
    resp = client.post(f"/api/v1/contracts/{contract_id}/start", headers=researcher_headers)
    assert resp.status_code == 402


def test_cannot_start_already_started_contract(client, researcher_headers, started_contract):
    """Cannot start a contract that is already in_progress (400)."""
    resp = client.post(f"/api/v1/contracts/{started_contract['contract_id']}/start",
                       headers=researcher_headers)
    assert resp.status_code == 400


def test_start_contract_requires_auth(client, full_contract):
    """POST /contracts/{id}/start requires authentication."""
    resp = client.post(f"/api/v1/contracts/{full_contract['contract_id']}/start")
    assert resp.status_code == 401


def test_wrong_researcher_cannot_start_contract(client, full_contract, db):
    """A different researcher cannot start a contract they don't own."""
    from tests.conftest import auth_headers
    other_researcher_headers = auth_headers(client, "researcher")
    resp = client.post(f"/api/v1/contracts/{full_contract['contract_id']}/start",
                       headers=other_researcher_headers)
    assert resp.status_code == 403
