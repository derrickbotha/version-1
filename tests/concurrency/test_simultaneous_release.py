"""
Concurrency tests: simultaneous release/refund prevention.

10 tests verifying idempotency of payment operations.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def _submit_and_approve(client, started_contract, researcher_headers, student_headers):
    contract_id = started_contract["contract_id"]
    client.post(
        "/api/v1/submissions",
        json={"contract_id": contract_id, "submission_notes": "Work completed"},
        headers=researcher_headers,
    )
    subs = client.get(f"/api/v1/contracts/{contract_id}/submissions", headers=student_headers)
    sub_id = subs.json()["data"]["items"][0]["id"]
    client.post(f"/api/v1/submissions/{sub_id}/approve", headers=student_headers)


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_release_payment_twice_second_returns_400(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
) -> None:
    _submit_and_approve(client, started_contract, researcher_headers, student_headers)
    contract_id = started_contract["contract_id"]

    r1 = client.post(
        "/api/v1/payments/release",
        json={"contract_id": contract_id},
        headers=student_headers,
    )
    assert r1.status_code == 200

    r2 = client.post(
        "/api/v1/payments/release",
        json={"contract_id": contract_id},
        headers=student_headers,
    )
    assert r2.status_code == 400


def test_refund_after_release_returns_400(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
) -> None:
    _submit_and_approve(client, started_contract, researcher_headers, student_headers)
    contract_id = started_contract["contract_id"]

    client.post(
        "/api/v1/payments/release",
        json={"contract_id": contract_id},
        headers=student_headers,
    )
    # Now try to refund
    resp = client.post(
        "/api/v1/payments/refund",
        json={"contract_id": contract_id, "reason": "Refund after release should fail"},
        headers=student_headers,
    )
    assert resp.status_code == 400


def test_release_after_refund_returns_400(
    client: TestClient,
    full_contract: dict,
    student_headers: dict,
) -> None:
    contract_id = full_contract["contract_id"]

    # Refund first
    client.post(
        "/api/v1/payments/refund",
        json={"contract_id": contract_id, "reason": "Refund before release test"},
        headers=student_headers,
    )
    # Try to release after refund
    resp = client.post(
        "/api/v1/payments/release",
        json={"contract_id": contract_id},
        headers=student_headers,
    )
    assert resp.status_code == 400


def test_double_refund_returns_400(
    client: TestClient,
    full_contract: dict,
    student_headers: dict,
) -> None:
    contract_id = full_contract["contract_id"]

    r1 = client.post(
        "/api/v1/payments/refund",
        json={"contract_id": contract_id, "reason": "First refund of contract"},
        headers=student_headers,
    )
    assert r1.status_code == 200

    r2 = client.post(
        "/api/v1/payments/refund",
        json={"contract_id": contract_id, "reason": "Second refund attempt should fail"},
        headers=student_headers,
    )
    assert r2.status_code == 400


def test_escrow_twice_returns_409(
    client: TestClient,
    student_headers: dict,
    researcher_headers: dict,
) -> None:
    """Creating escrow twice for same contract should fail."""
    job_resp = client.post(
        "/api/v1/jobs",
        json={"title": "Double Escrow Job", "description": "Testing double escrow prevention.",
              "subject": "CS", "academic_level": "Bachelors",
              "proposed_price": "100.00", "deadline": "2099-12-31T00:00:00Z"},
        headers=student_headers,
    )
    job_id = job_resp.json()["data"]["id"]
    bid_resp = client.post(
        f"/api/v1/jobs/{job_id}/bids",
        json={"proposed_price": "90.00", "message": "Double escrow test bid"},
        headers=researcher_headers,
    )
    bid_id = bid_resp.json()["data"]["id"]
    contract_id = client.post(f"/api/v1/bids/{bid_id}/accept", headers=student_headers).json()["data"]["id"]

    client.post(
        "/api/v1/payments/wallet/deposit",
        json={"amount": "500.00"},
        headers=student_headers,
    )
    e1 = client.post(
        "/api/v1/payments/escrow",
        json={"contract_id": contract_id, "payment_provider": "wallet", "provider_reference": "r1"},
        headers=student_headers,
    )
    assert e1.status_code in (200, 201)

    e2 = client.post(
        "/api/v1/payments/escrow",
        json={"contract_id": contract_id, "payment_provider": "wallet", "provider_reference": "r2"},
        headers=student_headers,
    )
    assert e2.status_code == 409


def test_start_contract_twice_returns_400(
    client: TestClient,
    full_contract: dict,
    researcher_headers: dict,
) -> None:
    contract_id = full_contract["contract_id"]
    r1 = client.post(f"/api/v1/contracts/{contract_id}/start", headers=researcher_headers)
    assert r1.status_code == 200

    r2 = client.post(f"/api/v1/contracts/{contract_id}/start", headers=researcher_headers)
    assert r2.status_code == 400


def test_release_on_completed_contract_returns_400(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
) -> None:
    """After contract is completed (status=completed), release should fail."""
    _submit_and_approve(client, started_contract, researcher_headers, student_headers)
    contract_id = started_contract["contract_id"]

    # Release payment
    client.post(
        "/api/v1/payments/release",
        json={"contract_id": contract_id},
        headers=student_headers,
    )
    # Contract is now completed — release again should fail
    resp = client.post(
        "/api/v1/payments/release",
        json={"contract_id": contract_id},
        headers=student_headers,
    )
    assert resp.status_code == 400


def test_approve_submission_twice_returns_error(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
) -> None:
    contract_id = started_contract["contract_id"]
    sub_resp = client.post(
        "/api/v1/submissions",
        json={"contract_id": contract_id, "submission_notes": "Work completed and ready for review"},
        headers=researcher_headers,
    )
    sub_id = sub_resp.json()["data"]["id"]

    r1 = client.post(f"/api/v1/submissions/{sub_id}/approve", headers=student_headers)
    assert r1.status_code == 200

    r2 = client.post(f"/api/v1/submissions/{sub_id}/approve", headers=student_headers)
    assert r2.status_code in (400, 409)


def test_refund_on_cancelled_contract_fails(
    client: TestClient,
    full_contract: dict,
    student_headers: dict,
) -> None:
    contract_id = full_contract["contract_id"]
    # Refund first (cancels contract)
    client.post(
        "/api/v1/payments/refund",
        json={"contract_id": contract_id, "reason": "Cancelling the contract"},
        headers=student_headers,
    )
    # Try to refund again — contract is cancelled, no escrowed payment
    resp = client.post(
        "/api/v1/payments/refund",
        json={"contract_id": contract_id, "reason": "Second refund attempt"},
        headers=student_headers,
    )
    assert resp.status_code == 400


def test_payout_approve_twice_returns_409(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
    admin_headers: dict,
) -> None:
    contract_id = started_contract["contract_id"]
    _submit_and_approve(client, started_contract, researcher_headers, student_headers)
    client.post("/api/v1/payments/release", json={"contract_id": contract_id}, headers=student_headers)

    payout_resp = client.post(
        "/api/v1/payments/payout",
        json={"amount": "50.00", "provider": "paypal"},
        headers=researcher_headers,
    )
    payout_id = payout_resp.json()["data"]["id"]

    r1 = client.post(f"/api/v1/admin/payouts/{payout_id}/approve", json={}, headers=admin_headers)
    assert r1.status_code == 200

    r2 = client.post(f"/api/v1/admin/payouts/{payout_id}/approve", json={}, headers=admin_headers)
    assert r2.status_code == 409
