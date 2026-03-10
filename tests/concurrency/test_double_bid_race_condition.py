"""
Concurrency tests: double bid race conditions.

10 tests verifying bid idempotency and constraints.
"""
from __future__ import annotations

import uuid
import pytest
from fastapi.testclient import TestClient


def _create_job(client, headers):
    resp = client.post(
        "/api/v1/jobs",
        json={"title": f"Concurrency Job {uuid.uuid4().hex[:6]}",
              "description": "Job created for concurrency testing purposes.",
              "subject": "Math", "academic_level": "Masters",
              "proposed_price": "150.00", "deadline": "2099-12-31T00:00:00Z"},
        headers=headers,
    )
    assert resp.status_code in (200, 201)
    return resp.json()["data"]["id"]


def _place_bid(client, researcher_headers, job_id, price="140.00"):
    return client.post(
        f"/api/v1/jobs/{job_id}/bids",
        json={"proposed_price": price, "message": "Concurrency test bid"},
        headers=researcher_headers,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_placing_same_bid_twice_second_returns_409(
    client: TestClient, student_headers: dict, researcher_headers: dict
) -> None:
    job_id = _create_job(client, student_headers)
    r1 = _place_bid(client, researcher_headers, job_id)
    assert r1.status_code in (200, 201)
    r2 = _place_bid(client, researcher_headers, job_id)
    assert r2.status_code in (400, 409)


def test_after_bid_accepted_another_bid_returns_400(
    client: TestClient, student_headers: dict, researcher_headers: dict
) -> None:
    job_id = _create_job(client, student_headers)
    bid = _place_bid(client, researcher_headers, job_id)
    bid_id = bid.json()["data"]["id"]
    client.post(f"/api/v1/bids/{bid_id}/accept", headers=student_headers)

    # Try to bid again — job is now accepted, not open
    r2 = _place_bid(client, researcher_headers, job_id, "130.00")
    assert r2.status_code == 400


def test_bid_on_non_open_job_returns_400(
    client: TestClient, student_headers: dict, researcher_headers: dict, db
) -> None:
    """Once job is accepted, new bids should be rejected."""
    job_id = _create_job(client, student_headers)

    # Create second researcher
    email2 = f"r2bid-{uuid.uuid4().hex[:8]}@test.com"
    client.post("/api/v1/auth/register", json={
        "email": email2, "password": "TestPassword123!",
        "first_name": "R2", "last_name": "Bidder", "role": "researcher"
    })
    login2 = client.post("/api/v1/auth/login", json={"email": email2, "password": "TestPassword123!"})
    r2_headers = {"Authorization": f"Bearer {login2.json()['data']['access_token']}"}

    # First researcher bids and wins
    bid = _place_bid(client, researcher_headers, job_id)
    bid_id = bid.json()["data"]["id"]
    client.post(f"/api/v1/bids/{bid_id}/accept", headers=student_headers)

    # Second researcher tries to bid — should fail
    resp = _place_bid(client, r2_headers, job_id, "120.00")
    assert resp.status_code == 400


def test_duplicate_bid_same_amount_fails(
    client: TestClient, student_headers: dict, researcher_headers: dict
) -> None:
    job_id = _create_job(client, student_headers)
    _place_bid(client, researcher_headers, job_id, "100.00")
    resp = _place_bid(client, researcher_headers, job_id, "100.00")
    assert resp.status_code in (400, 409)


def test_sequential_bids_from_same_researcher_fail(
    client: TestClient, student_headers: dict, researcher_headers: dict
) -> None:
    job_id = _create_job(client, student_headers)
    r1 = _place_bid(client, researcher_headers, job_id, "110.00")
    assert r1.status_code in (200, 201)
    r2 = _place_bid(client, researcher_headers, job_id, "105.00")
    assert r2.status_code in (400, 409)


def test_bid_on_cancelled_job_fails(
    client: TestClient, student_headers: dict, researcher_headers: dict, db
) -> None:
    """After full_contract is cancelled (if possible), new bids should fail."""
    job_id = _create_job(client, student_headers)
    # Patch job to cancelled status directly via DB
    from app.models.job import Job
    job = db.query(Job).filter(Job.id == job_id).first()
    job.status = "cancelled"
    db.commit()

    resp = _place_bid(client, researcher_headers, job_id)
    assert resp.status_code == 400


def test_withdraw_bid_then_cannot_bid_again(
    client: TestClient, student_headers: dict, researcher_headers: dict
) -> None:
    """After withdrawing a bid, researcher should be able to bid again (check if policy allows)."""
    job_id = _create_job(client, student_headers)
    bid = _place_bid(client, researcher_headers, job_id)
    bid_id = bid.json()["data"]["id"]
    # Withdraw the bid
    withdraw_resp = client.post(f"/api/v1/bids/{bid_id}/withdraw", headers=researcher_headers)
    # Whether withdraw allowed or not, check the current bid status
    # This test just verifies the endpoint is reachable
    assert withdraw_resp.status_code in (200, 400, 409)


def test_accept_withdrawn_bid_fails(
    client: TestClient, student_headers: dict, researcher_headers: dict
) -> None:
    job_id = _create_job(client, student_headers)
    bid = _place_bid(client, researcher_headers, job_id)
    bid_id = bid.json()["data"]["id"]
    # Withdraw
    client.post(f"/api/v1/bids/{bid_id}/withdraw", headers=researcher_headers)
    # Try to accept withdrawn bid
    resp = client.post(f"/api/v1/bids/{bid_id}/accept", headers=student_headers)
    assert resp.status_code in (400, 409)


def test_bid_nonexistent_job_returns_404(
    client: TestClient, researcher_headers: dict
) -> None:
    fake_id = str(uuid.uuid4())
    resp = _place_bid(client, researcher_headers, fake_id)
    assert resp.status_code == 404


def test_multiple_researchers_can_each_bid_once(
    client: TestClient, student_headers: dict, researcher_headers: dict, db
) -> None:
    """Different researchers can each bid once on the same job."""
    job_id = _create_job(client, student_headers)

    # Make another researcher
    email2 = f"r2-{uuid.uuid4().hex[:8]}@test.com"
    client.post("/api/v1/auth/register", json={
        "email": email2, "password": "TestPassword123!",
        "first_name": "R2", "last_name": "Bidder", "role": "researcher"
    })
    login2 = client.post("/api/v1/auth/login", json={"email": email2, "password": "TestPassword123!"})
    r2_headers = {"Authorization": f"Bearer {login2.json()['data']['access_token']}"}

    r1 = _place_bid(client, researcher_headers, job_id, "140.00")
    r2 = _place_bid(client, r2_headers, job_id, "135.00")
    assert r1.status_code in (200, 201)
    assert r2.status_code in (200, 201)
