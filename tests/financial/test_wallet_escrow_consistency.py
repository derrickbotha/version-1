"""
Financial tests: wallet and escrow balance consistency.

15 tests verifying wallet balances are correct after all operations.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def _get_wallet_balance(client, headers) -> float:
    resp = client.get("/api/v1/payments/wallet", headers=headers)
    if resp.status_code == 404:
        return 0.0
    return float(resp.json()["data"]["balance"])


def _deposit(client, headers, amount: str):
    resp = client.post(
        "/api/v1/payments/wallet/deposit",
        json={"amount": amount},
        headers=headers,
    )
    assert resp.status_code in (200, 201), resp.text
    return float(resp.json()["data"]["balance"])


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_wallet_balance_after_deposit(
    client: TestClient, student_headers: dict
) -> None:
    balance = _deposit(client, student_headers, "200.00")
    assert balance == 200.00


def test_wallet_balance_after_multiple_deposits(
    client: TestClient, student_headers: dict
) -> None:
    _deposit(client, student_headers, "100.00")
    _deposit(client, student_headers, "150.00")
    balance = _get_wallet_balance(client, student_headers)
    assert balance == 250.00


def test_sequential_deposits_accumulate(
    client: TestClient, student_headers: dict
) -> None:
    amounts = ["50.00", "75.00", "100.00"]
    for amt in amounts:
        _deposit(client, student_headers, amt)
    balance = _get_wallet_balance(client, student_headers)
    assert balance == 225.00


def test_wallet_balance_after_escrow(
    client: TestClient, full_contract: dict, student_headers: dict
) -> None:
    """Deposit was 500, escrow locked 180 (agreed_price), so balance should be ~320."""
    balance = _get_wallet_balance(client, student_headers)
    assert abs(balance - 320.00) < 0.01


def test_escrow_reduces_student_wallet_by_agreed_price(
    client: TestClient, full_contract: dict, student_headers: dict
) -> None:
    # Initial deposit was 500.00, agreed_price was 180.00
    balance = _get_wallet_balance(client, student_headers)
    expected = 500.00 - 180.00
    assert abs(balance - expected) < 0.01


def test_researcher_wallet_increases_after_release(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
) -> None:
    contract_id = started_contract["contract_id"]
    initial_balance = _get_wallet_balance(client, researcher_headers)

    client.post(
        "/api/v1/submissions",
        json={"contract_id": contract_id, "submission_notes": "Work done and completed"},
        headers=researcher_headers,
    )
    subs = client.get(f"/api/v1/contracts/{contract_id}/submissions", headers=student_headers)
    sub_id = subs.json()["data"]["items"][0]["id"]
    client.post(f"/api/v1/submissions/{sub_id}/approve", headers=student_headers)
    client.post(
        "/api/v1/payments/release",
        json={"contract_id": contract_id},
        headers=student_headers,
    )

    final_balance = _get_wallet_balance(client, researcher_headers)
    assert final_balance == initial_balance + 180.00


def test_student_wallet_restored_after_refund(
    client: TestClient,
    full_contract: dict,
    student_headers: dict,
) -> None:
    contract_id = full_contract["contract_id"]
    balance_before_refund = _get_wallet_balance(client, student_headers)

    client.post(
        "/api/v1/payments/refund",
        json={"contract_id": contract_id, "reason": "Project cancelled due to budget cuts"},
        headers=student_headers,
    )

    balance_after_refund = _get_wallet_balance(client, student_headers)
    # Balance should be restored by agreed_price (180)
    assert abs(balance_after_refund - (balance_before_refund + 180.00)) < 0.01


def test_wallet_balance_never_goes_negative(
    client: TestClient, student_headers: dict
) -> None:
    _deposit(client, student_headers, "50.00")
    balance = _get_wallet_balance(client, student_headers)
    assert balance >= 0


def test_transaction_count_matches_operations(
    client: TestClient, student_headers: dict, db: Session
) -> None:
    """Two deposits should create exactly 2 wallet transactions."""
    _deposit(client, student_headers, "100.00")
    _deposit(client, student_headers, "200.00")

    tx_resp = client.get("/api/v1/payments/wallet/transactions", headers=student_headers)
    data = tx_resp.json()["data"]
    deposit_txns = [t for t in data["items"] if t["transaction_type"] == "deposit"]
    assert len(deposit_txns) == 2


def test_escrow_creates_escrow_lock_transaction(
    client: TestClient, full_contract: dict, student_headers: dict
) -> None:
    tx_resp = client.get("/api/v1/payments/wallet/transactions", headers=student_headers)
    txns = tx_resp.json()["data"]["items"]
    tx_types = [t["transaction_type"] for t in txns]
    assert "escrow_lock" in tx_types


def test_refund_creates_refund_transaction(
    client: TestClient, full_contract: dict, student_headers: dict
) -> None:
    contract_id = full_contract["contract_id"]
    client.post(
        "/api/v1/payments/refund",
        json={"contract_id": contract_id, "reason": "Refund test for transaction verification"},
        headers=student_headers,
    )
    tx_resp = client.get("/api/v1/payments/wallet/transactions", headers=student_headers)
    txns = tx_resp.json()["data"]["items"]
    tx_types = [t["transaction_type"] for t in txns]
    assert "refund" in tx_types


def test_release_creates_payout_transaction_for_researcher(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
) -> None:
    contract_id = started_contract["contract_id"]
    client.post(
        "/api/v1/submissions",
        json={"contract_id": contract_id, "submission_notes": "Work completed and ready for review"},
        headers=researcher_headers,
    )
    subs = client.get(f"/api/v1/contracts/{contract_id}/submissions", headers=student_headers)
    sub_id = subs.json()["data"]["items"][0]["id"]
    client.post(f"/api/v1/submissions/{sub_id}/approve", headers=student_headers)
    client.post(
        "/api/v1/payments/release",
        json={"contract_id": contract_id},
        headers=student_headers,
    )

    tx_resp = client.get("/api/v1/payments/wallet/transactions", headers=researcher_headers)
    txns = tx_resp.json()["data"]["items"]
    tx_types = [t["transaction_type"] for t in txns]
    assert "payout" in tx_types


def test_insufficient_balance_escrow_returns_402(
    client: TestClient, student_headers: dict, researcher_headers: dict
) -> None:
    """Escrow fails if student doesn't have enough balance."""
    # Create job/bid/accept without depositing enough
    job_resp = client.post(
        "/api/v1/jobs",
        json={"title": "Insufficient Balance Job",
              "description": "Job for insufficient balance test scenario.",
              "subject": "Math", "academic_level": "Masters",
              "proposed_price": "1000.00", "deadline": "2099-12-31T00:00:00Z"},
        headers=student_headers,
    )
    job_id = job_resp.json()["data"]["id"]
    bid_resp = client.post(
        f"/api/v1/jobs/{job_id}/bids",
        json={"proposed_price": "900.00", "message": "Big bid for insufficient balance test"},
        headers=researcher_headers,
    )
    bid_id = bid_resp.json()["data"]["id"]
    accept_resp = client.post(f"/api/v1/bids/{bid_id}/accept", headers=student_headers)
    contract_id = accept_resp.json()["data"]["id"]

    # Only deposit 50, not enough for 900
    client.post("/api/v1/payments/wallet/deposit", json={"amount": "50.00"}, headers=student_headers)

    resp = client.post(
        "/api/v1/payments/escrow",
        json={"contract_id": contract_id, "payment_provider": "wallet",
              "provider_reference": "test"},
        headers=student_headers,
    )
    assert resp.status_code == 402


def test_wallet_balance_correct_after_deposit_then_escrow_then_refund(
    client: TestClient, full_contract: dict, student_headers: dict
) -> None:
    """deposit(500) -> escrow(180) -> refund => balance should be 500."""
    contract_id = full_contract["contract_id"]
    client.post(
        "/api/v1/payments/refund",
        json={"contract_id": contract_id, "reason": "Refund complete cycle test"},
        headers=student_headers,
    )
    balance = _get_wallet_balance(client, student_headers)
    assert abs(balance - 500.00) < 0.01
