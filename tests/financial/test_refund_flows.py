"""
Financial tests: refund flows.

15 tests covering various refund scenarios.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_refund_on_escrowed_contract_returns_funds_to_student(
    client: TestClient,
    full_contract: dict,
    student_headers: dict,
) -> None:
    contract_id = full_contract["contract_id"]
    balance_before = float(client.get("/api/v1/payments/wallet", headers=student_headers).json()["data"]["balance"])

    resp = client.post(
        "/api/v1/payments/refund",
        json={"contract_id": contract_id, "reason": "Project cancelled by student"},
        headers=student_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "refunded"

    balance_after = float(client.get("/api/v1/payments/wallet", headers=student_headers).json()["data"]["balance"])
    assert balance_after > balance_before


def test_refund_on_non_escrowed_contract_returns_400(
    client: TestClient,
    student_headers: dict,
    researcher_headers: dict,
) -> None:
    """Refund on contract with no escrowed payment fails."""
    job_resp = client.post(
        "/api/v1/jobs",
        json={"title": "No Escrow Job", "description": "Testing refund on non-escrowed contract.",
              "subject": "Physics", "academic_level": "Bachelors",
              "proposed_price": "50.00", "deadline": "2099-12-31T00:00:00Z"},
        headers=student_headers,
    )
    job_id = job_resp.json()["data"]["id"]
    bid_resp = client.post(
        f"/api/v1/jobs/{job_id}/bids",
        json={"proposed_price": "45.00", "message": "Non-escrowed test bid"},
        headers=researcher_headers,
    )
    bid_id = bid_resp.json()["data"]["id"]
    accept_resp = client.post(f"/api/v1/bids/{bid_id}/accept", headers=student_headers)
    contract_id = accept_resp.json()["data"]["id"]

    # Try to refund without escrow
    resp = client.post(
        "/api/v1/payments/refund",
        json={"contract_id": contract_id, "reason": "Refund before escrow should fail"},
        headers=student_headers,
    )
    assert resp.status_code == 400


def test_refund_sets_contract_to_cancelled(
    client: TestClient,
    full_contract: dict,
    student_headers: dict,
) -> None:
    contract_id = full_contract["contract_id"]
    client.post(
        "/api/v1/payments/refund",
        json={"contract_id": contract_id, "reason": "Testing contract cancellation on refund"},
        headers=student_headers,
    )
    contract_resp = client.get(f"/api/v1/contracts/{contract_id}", headers=student_headers)
    assert contract_resp.json()["data"]["status"] == "cancelled"


def test_refund_creates_wallet_transaction_of_type_refund(
    client: TestClient,
    full_contract: dict,
    student_headers: dict,
) -> None:
    contract_id = full_contract["contract_id"]
    client.post(
        "/api/v1/payments/refund",
        json={"contract_id": contract_id, "reason": "Testing refund transaction type"},
        headers=student_headers,
    )
    tx_resp = client.get("/api/v1/payments/wallet/transactions", headers=student_headers)
    txns = tx_resp.json()["data"]["items"]
    refund_txns = [t for t in txns if t["transaction_type"] == "refund"]
    assert len(refund_txns) >= 1


def test_admin_can_refund_any_contract(
    client: TestClient,
    full_contract: dict,
    admin_headers: dict,
) -> None:
    contract_id = full_contract["contract_id"]
    resp = client.post(
        "/api/v1/payments/refund",
        json={"contract_id": contract_id, "reason": "Admin refund for policy violation"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "refunded"


def test_after_refund_student_can_post_new_jobs(
    client: TestClient,
    full_contract: dict,
    student_headers: dict,
) -> None:
    contract_id = full_contract["contract_id"]
    client.post(
        "/api/v1/payments/refund",
        json={"contract_id": contract_id, "reason": "Refund test — new job after refund"},
        headers=student_headers,
    )
    # Student can still post new jobs
    resp = client.post(
        "/api/v1/jobs",
        json={"title": "New Job After Refund",
              "description": "Testing that student can post new jobs after getting a refund.",
              "subject": "Biology", "academic_level": "Bachelors",
              "proposed_price": "75.00", "deadline": "2099-12-31T00:00:00Z"},
        headers=student_headers,
    )
    assert resp.status_code in (200, 201)


def test_double_refund_returns_400(
    client: TestClient,
    full_contract: dict,
    student_headers: dict,
) -> None:
    contract_id = full_contract["contract_id"]
    client.post(
        "/api/v1/payments/refund",
        json={"contract_id": contract_id, "reason": "First refund request"},
        headers=student_headers,
    )
    resp = client.post(
        "/api/v1/payments/refund",
        json={"contract_id": contract_id, "reason": "Second refund request should fail"},
        headers=student_headers,
    )
    assert resp.status_code == 400


def test_refund_on_released_contract_fails(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
) -> None:
    contract_id = started_contract["contract_id"]
    # Complete contract
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
    # Try to refund after release
    resp = client.post(
        "/api/v1/payments/refund",
        json={"contract_id": contract_id, "reason": "Refund after release should fail"},
        headers=student_headers,
    )
    assert resp.status_code == 400


def test_researcher_cannot_refund_own_contract(
    client: TestClient,
    full_contract: dict,
    researcher_headers: dict,
) -> None:
    contract_id = full_contract["contract_id"]
    resp = client.post(
        "/api/v1/payments/refund",
        json={"contract_id": contract_id, "reason": "Researcher requesting refund should fail"},
        headers=researcher_headers,
    )
    assert resp.status_code == 403


def test_refund_amount_equals_agreed_price(
    client: TestClient,
    full_contract: dict,
    student_headers: dict,
) -> None:
    contract_id = full_contract["contract_id"]
    balance_before = float(client.get("/api/v1/payments/wallet", headers=student_headers).json()["data"]["balance"])

    client.post(
        "/api/v1/payments/refund",
        json={"contract_id": contract_id, "reason": "Test refund amount check"},
        headers=student_headers,
    )
    balance_after = float(client.get("/api/v1/payments/wallet", headers=student_headers).json()["data"]["balance"])
    refund_amount = balance_after - balance_before
    assert abs(refund_amount - 180.00) < 0.01  # agreed_price from conftest


def test_refund_payment_status_is_refunded(
    client: TestClient,
    full_contract: dict,
    student_headers: dict,
) -> None:
    contract_id = full_contract["contract_id"]
    resp = client.post(
        "/api/v1/payments/refund",
        json={"contract_id": contract_id, "reason": "Checking payment status after refund"},
        headers=student_headers,
    )
    assert resp.json()["data"]["status"] == "refunded"


def test_refund_on_nonexistent_contract_returns_404(
    client: TestClient, student_headers: dict
) -> None:
    import uuid
    fake_id = str(uuid.uuid4())
    resp = client.post(
        "/api/v1/payments/refund",
        json={"contract_id": fake_id, "reason": "Refund on nonexistent contract"},
        headers=student_headers,
    )
    assert resp.status_code == 404


def test_unauthenticated_cannot_refund(
    client: TestClient, full_contract: dict
) -> None:
    contract_id = full_contract["contract_id"]
    resp = client.post(
        "/api/v1/payments/refund",
        json={"contract_id": contract_id, "reason": "Unauthenticated refund"},
    )
    assert resp.status_code == 401


def test_refund_on_in_progress_contract(
    client: TestClient,
    started_contract: dict,
    student_headers: dict,
) -> None:
    """Student can request refund on in_progress contract."""
    contract_id = started_contract["contract_id"]
    resp = client.post(
        "/api/v1/payments/refund",
        json={"contract_id": contract_id, "reason": "Changed mind after work started"},
        headers=student_headers,
    )
    # in_progress contract has escrowed payment, so refund should work
    assert resp.status_code == 200


def test_refund_notified_in_wallet_transaction_history(
    client: TestClient,
    full_contract: dict,
    student_headers: dict,
) -> None:
    contract_id = full_contract["contract_id"]
    client.post(
        "/api/v1/payments/refund",
        json={"contract_id": contract_id, "reason": "Verifying refund in transaction history"},
        headers=student_headers,
    )
    tx_resp = client.get(
        "/api/v1/payments/wallet/transactions",
        headers=student_headers,
    )
    assert tx_resp.status_code == 200
    txns = tx_resp.json()["data"]["items"]
    assert any(t["transaction_type"] == "refund" for t in txns)
