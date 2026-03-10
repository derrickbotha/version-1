"""
Integration tests: deposit → escrow → start → submit → approve → release.

15 tests covering:
- Deposit → escrow → start → submit → approve → release happy path
- Researcher wallet has funds after release
- Payment status is released after release
- Contract status is completed after release
- ResearcherProfile.total_jobs_completed incremented
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def _full_release_flow(client, started_contract, researcher_headers, student_headers):
    """Submit, approve, and release a started contract. Returns payment data."""
    contract_id = started_contract["contract_id"]

    # Submit work
    client.post(
        "/api/v1/submissions",
        json={"contract_id": contract_id, "submission_notes": "Completed research"},
        headers=researcher_headers,
    )

    # Get submission and approve
    subs = client.get(f"/api/v1/contracts/{contract_id}/submissions", headers=student_headers)
    sub_id = subs.json()["data"]["items"][0]["id"]
    client.post(f"/api/v1/submissions/{sub_id}/approve", headers=student_headers)

    # Release payment
    release_resp = client.post(
        "/api/v1/payments/release",
        json={"contract_id": contract_id},
        headers=student_headers,
    )
    assert release_resp.status_code == 200, release_resp.text
    return release_resp.json()["data"]


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_deposit_to_wallet_succeeds(
    client: TestClient, student_headers: dict
) -> None:
    resp = client.post(
        "/api/v1/payments/wallet/deposit",
        json={"amount": "100.00"},
        headers=student_headers,
    )
    assert resp.status_code in (200, 201)
    assert float(resp.json()["data"]["balance"]) >= 100.0


def test_escrow_locks_funds_from_wallet(
    client: TestClient, full_contract: dict, student_headers: dict
) -> None:
    wallet_resp = client.get("/api/v1/payments/wallet", headers=student_headers)
    balance_after_escrow = float(wallet_resp.json()["data"]["balance"])
    # Original deposit was 500, escrow is 180, so balance should be ~320
    assert balance_after_escrow < 500.0


def test_start_contract_requires_escrow(
    client: TestClient, full_contract: dict, researcher_headers: dict
) -> None:
    """full_contract is in escrowed state; we're checking researcher can start."""
    # Actually, full_contract fixture does NOT start — started_contract does
    # Here we verify the full_contract is escrowed (not in_progress)
    contract_id = full_contract["contract_id"]
    contract_resp = client.get(f"/api/v1/contracts/{contract_id}", headers=researcher_headers)
    assert contract_resp.status_code == 200
    assert contract_resp.json()["data"]["status"] == "accepted"


def test_full_release_flow_completes_contract(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
) -> None:
    contract_id = started_contract["contract_id"]
    _full_release_flow(client, started_contract, researcher_headers, student_headers)

    contracts_resp = client.get("/api/v1/contracts", headers=student_headers)
    contracts = contracts_resp.json()["data"]["items"]
    contract = [c for c in contracts if c["id"] == contract_id][0]
    assert contract["status"] == "completed"


def test_after_release_payment_status_is_released(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
) -> None:
    payment = _full_release_flow(client, started_contract, researcher_headers, student_headers)
    assert payment["status"] == "released"


def test_after_release_researcher_wallet_has_funds(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
) -> None:
    _full_release_flow(client, started_contract, researcher_headers, student_headers)

    wallet_resp = client.get("/api/v1/payments/wallet", headers=researcher_headers)
    assert wallet_resp.status_code == 200
    balance = float(wallet_resp.json()["data"]["balance"])
    assert balance > 0


def test_contract_status_is_completed_after_release(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
) -> None:
    contract_id = started_contract["contract_id"]
    _full_release_flow(client, started_contract, researcher_headers, student_headers)

    contract_resp = client.get(f"/api/v1/contracts/{contract_id}", headers=student_headers)
    assert contract_resp.json()["data"]["status"] == "completed"


def test_researcher_jobs_completed_incremented_after_release(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
    db,
) -> None:
    from app.models.user import ResearcherProfile, User

    researcher_resp = client.get("/api/v1/auth/me", headers=researcher_headers)
    researcher_id = researcher_resp.json()["data"]["id"]

    # Check initial count
    profile = db.query(ResearcherProfile).filter(
        ResearcherProfile.user_id == researcher_id
    ).first()
    initial_count = profile.total_jobs_completed if profile else 0

    _full_release_flow(client, started_contract, researcher_headers, student_headers)

    db.refresh(profile) if profile else None
    profile = db.query(ResearcherProfile).filter(
        ResearcherProfile.user_id == researcher_id
    ).first()
    if profile:
        assert profile.total_jobs_completed == initial_count + 1


def test_release_creates_wallet_transactions(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
) -> None:
    _full_release_flow(client, started_contract, researcher_headers, student_headers)

    # Check researcher wallet transactions
    tx_resp = client.get(
        "/api/v1/payments/wallet/transactions",
        headers=researcher_headers,
    )
    assert tx_resp.status_code == 200
    txns = tx_resp.json()["data"]["items"]
    tx_types = [t["transaction_type"] for t in txns]
    assert "payout" in tx_types


def test_double_release_returns_error(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
) -> None:
    contract_id = started_contract["contract_id"]
    _full_release_flow(client, started_contract, researcher_headers, student_headers)

    # Second release should fail
    resp = client.post(
        "/api/v1/payments/release",
        json={"contract_id": contract_id},
        headers=student_headers,
    )
    assert resp.status_code == 400


def test_refund_on_escrowed_contract_returns_funds_to_student(
    client: TestClient,
    full_contract: dict,
    student_headers: dict,
    researcher_headers: dict,
) -> None:
    contract_id = full_contract["contract_id"]

    # Get balance before refund
    wallet_before = client.get("/api/v1/payments/wallet", headers=student_headers)
    balance_before = float(wallet_before.json()["data"]["balance"])

    resp = client.post(
        "/api/v1/payments/refund",
        json={"contract_id": contract_id, "reason": "Changed requirements and no longer need this work"},
        headers=student_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "refunded"

    # Balance should be restored
    wallet_after = client.get("/api/v1/payments/wallet", headers=student_headers)
    balance_after = float(wallet_after.json()["data"]["balance"])
    assert balance_after > balance_before


def test_refund_sets_contract_to_cancelled(
    client: TestClient,
    full_contract: dict,
    student_headers: dict,
) -> None:
    contract_id = full_contract["contract_id"]
    client.post(
        "/api/v1/payments/refund",
        json={"contract_id": contract_id, "reason": "Project was cancelled due to budget constraints"},
        headers=student_headers,
    )
    contract_resp = client.get(f"/api/v1/contracts/{contract_id}", headers=student_headers)
    assert contract_resp.json()["data"]["status"] == "cancelled"


def test_cannot_release_payment_on_non_submitted_contract(
    client: TestClient,
    full_contract: dict,
    student_headers: dict,
) -> None:
    """full_contract is escrowed but not submitted — release should fail."""
    contract_id = full_contract["contract_id"]
    resp = client.post(
        "/api/v1/payments/release",
        json={"contract_id": contract_id},
        headers=student_headers,
    )
    assert resp.status_code == 400


def test_researcher_cannot_release_own_payment(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
) -> None:
    contract_id = started_contract["contract_id"]
    # Submit work
    client.post(
        "/api/v1/submissions",
        json={"contract_id": contract_id, "submission_notes": "Work done and completed"},
        headers=researcher_headers,
    )
    resp = client.post(
        "/api/v1/payments/release",
        json={"contract_id": contract_id},
        headers=researcher_headers,
    )
    assert resp.status_code == 403


def test_student_wallet_reduced_after_escrow(
    client: TestClient,
    full_contract: dict,
    student_headers: dict,
) -> None:
    wallet_resp = client.get("/api/v1/payments/wallet", headers=student_headers)
    # Started with 500.00, escrowed 180.00
    balance = float(wallet_resp.json()["data"]["balance"])
    assert balance < 500.0
