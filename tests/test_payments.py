"""
Tests for the payment endpoints:
  POST /api/v1/payments/wallet/deposit
  GET  /api/v1/payments/wallet
  POST /api/v1/payments/escrow
  POST /api/v1/payments/release
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _deposit(client: TestClient, headers: dict, amount: str = "500.00") -> object:
    return client.post(
        "/api/v1/payments/wallet/deposit",
        json={"amount": amount},
        headers=headers,
    )


def _create_contract(
    client: TestClient,
    student_headers: dict,
    researcher_headers: dict,
) -> dict:
    """
    Full flow to obtain a contract in 'accepted' status:
    1. Create a job (student).
    2. Place a bid (researcher).
    3. Accept the bid (student) → contract returned.
    """
    job_resp = client.post(
        "/api/v1/jobs",
        json={
            "title": "Payment Flow Research Job",
            "description": "A test job created to exercise the payment escrow flow end to end.",
            "subject": "Economics",
            "academic_level": "PhD",
            "proposed_price": "300.00",
            "deadline": "2099-09-01T00:00:00Z",
        },
        headers=student_headers,
    )
    assert job_resp.status_code in (200, 201), f"Create job failed: {job_resp.text}"
    job_id = job_resp.json()["data"]["id"]

    bid_resp = client.post(
        f"/api/v1/jobs/{job_id}/bids",
        json={
            "proposed_price": "280.00",
            "message": "I am highly qualified to complete this economic research assignment.",
        },
        headers=researcher_headers,
    )
    assert bid_resp.status_code in (200, 201), f"Place bid failed: {bid_resp.text}"
    bid_id = bid_resp.json()["data"]["id"]

    accept_resp = client.post(
        f"/api/v1/bids/{bid_id}/accept",
        headers=student_headers,
    )
    assert accept_resp.status_code == 200, f"Accept bid failed: {accept_resp.text}"
    return accept_resp.json()["data"]


# ---------------------------------------------------------------------------
# Wallet deposit
# ---------------------------------------------------------------------------

def test_deposit_to_wallet(client: TestClient, student_headers: dict) -> None:
    """Depositing funds updates the wallet balance."""
    resp = _deposit(client, student_headers, "250.00")
    assert resp.status_code in (200, 201)
    data = resp.json()["data"]
    assert "balance" in data
    # Balance should be at least 250 after the deposit
    assert float(data["balance"]) >= 250.0


def test_deposit_invalid_amount(client: TestClient, student_headers: dict) -> None:
    """Depositing zero or negative amount returns 422."""
    resp = client.post(
        "/api/v1/payments/wallet/deposit",
        json={"amount": "0.00"},
        headers=student_headers,
    )
    assert resp.status_code == 422


def test_deposit_unauthenticated(client: TestClient) -> None:
    """Unauthenticated deposit attempt returns 401."""
    resp = client.post(
        "/api/v1/payments/wallet/deposit",
        json={"amount": "100.00"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Wallet balance
# ---------------------------------------------------------------------------

def test_get_wallet(client: TestClient, student_headers: dict) -> None:
    """GET /api/v1/payments/wallet returns the wallet with a balance field."""
    _deposit(client, student_headers, "100.00")  # ensure wallet exists

    resp = client.get("/api/v1/payments/wallet", headers=student_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "balance" in data
    assert "user_id" in data


def test_get_wallet_unauthenticated(client: TestClient) -> None:
    """Unauthenticated GET /wallet returns 401."""
    resp = client.get("/api/v1/payments/wallet")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Escrow creation
# ---------------------------------------------------------------------------

def test_create_escrow(
    client: TestClient,
    student_headers: dict,
    researcher_headers: dict,
) -> None:
    """After accepting a bid, a student with sufficient funds can create escrow."""
    contract = _create_contract(client, student_headers, researcher_headers)
    contract_id = contract["id"]

    # Deposit enough funds
    _deposit(client, student_headers, "500.00")

    escrow_resp = client.post(
        "/api/v1/payments/escrow",
        json={
            "contract_id": contract_id,
            "payment_provider": "manual",
            "provider_reference": f"test-ref-{uuid.uuid4().hex[:8]}",
        },
        headers=student_headers,
    )
    assert escrow_resp.status_code in (200, 201)
    data = escrow_resp.json()["data"]
    assert data["status"] == "escrowed"
    assert data["contract_id"] == contract_id


def test_insufficient_balance(
    client: TestClient,
    student_headers: dict,
    researcher_headers: dict,
) -> None:
    """
    Attempting to create escrow with insufficient wallet balance returns 402.
    We do NOT deposit any funds here.
    """
    contract = _create_contract(client, student_headers, researcher_headers)
    contract_id = contract["id"]

    # Do NOT deposit — wallet balance is zero (or freshly created user)
    escrow_resp = client.post(
        "/api/v1/payments/escrow",
        json={
            "contract_id": contract_id,
            "payment_provider": "manual",
            "provider_reference": f"test-ref-{uuid.uuid4().hex[:8]}",
        },
        headers=student_headers,
    )
    assert escrow_resp.status_code == 402


def test_duplicate_escrow(
    client: TestClient,
    student_headers: dict,
    researcher_headers: dict,
) -> None:
    """Creating a second escrow for the same contract returns 409."""
    contract = _create_contract(client, student_headers, researcher_headers)
    contract_id = contract["id"]

    # Deposit generously
    _deposit(client, student_headers, "1000.00")

    ref = f"ref-{uuid.uuid4().hex[:8]}"
    client.post(
        "/api/v1/payments/escrow",
        json={"contract_id": contract_id, "payment_provider": "manual", "provider_reference": ref},
        headers=student_headers,
    )

    # Second attempt
    resp = client.post(
        "/api/v1/payments/escrow",
        json={"contract_id": contract_id, "payment_provider": "manual", "provider_reference": ref},
        headers=student_headers,
    )
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Payment release
# ---------------------------------------------------------------------------

def test_release_payment(
    client: TestClient,
    student_headers: dict,
    researcher_headers: dict,
    db,  # noqa: ANN001
) -> None:
    """
    After creating escrow, a student can release the payment if the contract
    is moved to 'submitted' status.

    We directly update the contract status in the DB to simulate submission,
    then call the release endpoint.
    """
    from app.models.contract import Contract  # noqa: PLC0415

    contract = _create_contract(client, student_headers, researcher_headers)
    contract_id = contract["id"]

    _deposit(client, student_headers, "1000.00")

    client.post(
        "/api/v1/payments/escrow",
        json={
            "contract_id": contract_id,
            "payment_provider": "manual",
            "provider_reference": f"ref-{uuid.uuid4().hex[:8]}",
        },
        headers=student_headers,
    )

    # Simulate researcher submitting work by setting contract status directly
    db_contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if db_contract:
        db_contract.status = "submitted"
        db.commit()

    release_resp = client.post(
        "/api/v1/payments/release",
        json={"contract_id": contract_id},
        headers=student_headers,
    )
    assert release_resp.status_code == 200
    data = release_resp.json()["data"]
    assert data["status"] == "released"
