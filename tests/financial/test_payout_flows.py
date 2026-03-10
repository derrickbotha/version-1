"""
Financial tests: payout flows.

15 tests covering researcher payout lifecycle.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def _complete_and_release(client, started_contract, researcher_headers, student_headers):
    """Complete a contract and release payment."""
    contract_id = started_contract["contract_id"]
    client.post(
        "/api/v1/submissions",
        json={"contract_id": contract_id, "submission_notes": "Completed work"},
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


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_researcher_can_request_payout_after_payment(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
) -> None:
    _complete_and_release(client, started_contract, researcher_headers, student_headers)
    resp = client.post(
        "/api/v1/payments/payout",
        json={"amount": "100.00", "provider": "paypal"},
        headers=researcher_headers,
    )
    assert resp.status_code in (200, 201)
    assert resp.json()["data"]["status"] == "pending"


def test_payout_with_insufficient_balance_returns_402(
    client: TestClient,
    researcher_headers: dict,
) -> None:
    # No payment received, balance should be zero
    resp = client.post(
        "/api/v1/payments/payout",
        json={"amount": "500.00", "provider": "paypal"},
        headers=researcher_headers,
    )
    assert resp.status_code == 402


def test_payout_reduces_researcher_wallet_balance(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
) -> None:
    _complete_and_release(client, started_contract, researcher_headers, student_headers)
    balance_before = float(client.get("/api/v1/payments/wallet", headers=researcher_headers).json()["data"]["balance"])

    client.post(
        "/api/v1/payments/payout",
        json={"amount": "100.00", "provider": "paypal"},
        headers=researcher_headers,
    )

    balance_after = float(client.get("/api/v1/payments/wallet", headers=researcher_headers).json()["data"]["balance"])
    assert balance_after == balance_before - 100.00


def test_payout_creates_writer_payout_record_with_pending_status(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
) -> None:
    _complete_and_release(client, started_contract, researcher_headers, student_headers)
    resp = client.post(
        "/api/v1/payments/payout",
        json={"amount": "50.00", "provider": "paypal"},
        headers=researcher_headers,
    )
    assert resp.json()["data"]["status"] == "pending"
    assert resp.json()["data"]["id"] is not None


def test_admin_approves_payout_changes_status_to_processing(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
    admin_headers: dict,
) -> None:
    _complete_and_release(client, started_contract, researcher_headers, student_headers)
    payout_resp = client.post(
        "/api/v1/payments/payout",
        json={"amount": "80.00", "provider": "paypal"},
        headers=researcher_headers,
    )
    payout_id = payout_resp.json()["data"]["id"]

    admin_resp = client.post(
        f"/api/v1/admin/payouts/{payout_id}/approve",
        json={"notes": "Approved"},
        headers=admin_headers,
    )
    assert admin_resp.status_code == 200
    assert admin_resp.json()["data"]["status"] == "processing"


def test_admin_rejects_payout_returns_funds(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
    admin_headers: dict,
) -> None:
    _complete_and_release(client, started_contract, researcher_headers, student_headers)
    balance_before_payout = float(client.get("/api/v1/payments/wallet", headers=researcher_headers).json()["data"]["balance"])

    payout_resp = client.post(
        "/api/v1/payments/payout",
        json={"amount": "100.00", "provider": "paypal"},
        headers=researcher_headers,
    )
    payout_id = payout_resp.json()["data"]["id"]

    client.post(
        f"/api/v1/admin/payouts/{payout_id}/reject",
        json={"reason": "Invalid bank account details provided"},
        headers=admin_headers,
    )

    # Balance should be refunded
    balance_after_rejection = float(client.get("/api/v1/payments/wallet", headers=researcher_headers).json()["data"]["balance"])
    assert balance_after_rejection == balance_before_payout


def test_researcher_can_list_own_payouts(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
) -> None:
    _complete_and_release(client, started_contract, researcher_headers, student_headers)
    client.post(
        "/api/v1/payments/payout",
        json={"amount": "60.00", "provider": "paypal"},
        headers=researcher_headers,
    )
    resp = client.get("/api/v1/payments/payouts", headers=researcher_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] >= 1


def test_payout_creates_payout_wallet_transaction(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
) -> None:
    _complete_and_release(client, started_contract, researcher_headers, student_headers)
    client.post(
        "/api/v1/payments/payout",
        json={"amount": "70.00", "provider": "paypal"},
        headers=researcher_headers,
    )
    tx_resp = client.get("/api/v1/payments/wallet/transactions", headers=researcher_headers)
    txns = tx_resp.json()["data"]["items"]
    payout_txns = [t for t in txns if t["transaction_type"] == "payout"]
    assert len(payout_txns) >= 2  # one from release, one from payout request


def test_student_cannot_request_payout(
    client: TestClient,
    student_headers: dict,
) -> None:
    resp = client.post(
        "/api/v1/payments/payout",
        json={"amount": "50.00", "provider": "paypal"},
        headers=student_headers,
    )
    assert resp.status_code == 403


def test_payout_requires_minimum_amount(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
) -> None:
    _complete_and_release(client, started_contract, researcher_headers, student_headers)
    # Request zero amount
    resp = client.post(
        "/api/v1/payments/payout",
        json={"amount": "0.00", "provider": "paypal"},
        headers=researcher_headers,
    )
    # Should fail (insufficient or validation error)
    assert resp.status_code in (402, 422)


def test_payout_provider_required(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
) -> None:
    _complete_and_release(client, started_contract, researcher_headers, student_headers)
    resp = client.post(
        "/api/v1/payments/payout",
        json={"amount": "50.00"},  # Missing provider
        headers=researcher_headers,
    )
    assert resp.status_code == 422


def test_payout_listed_in_admin_payouts(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
    admin_headers: dict,
) -> None:
    _complete_and_release(client, started_contract, researcher_headers, student_headers)
    client.post(
        "/api/v1/payments/payout",
        json={"amount": "90.00", "provider": "paypal"},
        headers=researcher_headers,
    )
    resp = client.get("/api/v1/admin/payouts", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] >= 1


def test_approve_already_approved_payout_returns_409(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
    admin_headers: dict,
) -> None:
    _complete_and_release(client, started_contract, researcher_headers, student_headers)
    payout_resp = client.post(
        "/api/v1/payments/payout",
        json={"amount": "80.00", "provider": "paypal"},
        headers=researcher_headers,
    )
    payout_id = payout_resp.json()["data"]["id"]

    client.post(f"/api/v1/admin/payouts/{payout_id}/approve", json={}, headers=admin_headers)
    resp = client.post(f"/api/v1/admin/payouts/{payout_id}/approve", json={}, headers=admin_headers)
    assert resp.status_code == 409


def test_payout_amount_matches_requested_amount(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
) -> None:
    _complete_and_release(client, started_contract, researcher_headers, student_headers)
    resp = client.post(
        "/api/v1/payments/payout",
        json={"amount": "77.50", "provider": "paypal"},
        headers=researcher_headers,
    )
    assert float(resp.json()["data"]["amount"]) == 77.50
