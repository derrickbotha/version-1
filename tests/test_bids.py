"""
Tests for the bid endpoints:
  POST /api/v1/jobs/{id}/bids
  POST /api/v1/bids/{id}/accept
  POST /api/v1/bids/{id}/reject
  POST /api/v1/bids/{id}/counter
  POST /api/v1/bids/{id}/withdraw
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BID_PAYLOAD = {
    "proposed_price": "120.00",
    "message": "I have extensive experience in this research area and can deliver quality results.",
}


def _place_bid(
    client: TestClient,
    job_id: str,
    headers: dict,
    payload: dict | None = None,
) -> object:
    return client.post(
        f"/api/v1/jobs/{job_id}/bids",
        json=payload or BID_PAYLOAD,
        headers=headers,
    )


# ---------------------------------------------------------------------------
# Placing bids
# ---------------------------------------------------------------------------

def test_place_bid_as_researcher(
    client: TestClient,
    researcher_headers: dict,
    sample_job: dict,
) -> None:
    """A researcher can place a bid on an open job."""
    resp = _place_bid(client, sample_job["id"], researcher_headers)
    assert resp.status_code in (200, 201)
    data = resp.json()["data"]
    assert data["status"] == "pending"
    assert data["job_id"] == sample_job["id"]


def test_place_bid_as_student(
    client: TestClient,
    student_headers: dict,
    sample_job: dict,
) -> None:
    """A student cannot place bids — expect 403."""
    resp = _place_bid(client, sample_job["id"], student_headers)
    assert resp.status_code == 403


def test_place_bid_unauthenticated(client: TestClient, sample_job: dict) -> None:
    """Unauthenticated bid placement returns 401."""
    resp = _place_bid(client, sample_job["id"], {})
    assert resp.status_code == 401


def test_duplicate_bid(
    client: TestClient,
    researcher_headers: dict,
    sample_job: dict,
) -> None:
    """The same researcher cannot place two active bids on the same job — expect 400."""
    _place_bid(client, sample_job["id"], researcher_headers)
    resp = _place_bid(client, sample_job["id"], researcher_headers)
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Accepting bids
# ---------------------------------------------------------------------------

def test_accept_bid(
    client: TestClient,
    student_headers: dict,
    researcher_headers: dict,
    sample_job: dict,
) -> None:
    """A student can accept a pending bid; a contract is created."""
    bid_resp = _place_bid(client, sample_job["id"], researcher_headers)
    assert bid_resp.status_code in (200, 201)
    bid_id = bid_resp.json()["data"]["id"]

    accept_resp = client.post(
        f"/api/v1/bids/{bid_id}/accept",
        headers=student_headers,
    )
    assert accept_resp.status_code == 200
    data = accept_resp.json()["data"]
    # Response should be a contract
    assert "id" in data
    assert data["status"] == "accepted"


def test_accept_bid_as_researcher_forbidden(
    client: TestClient,
    student_headers: dict,
    researcher_headers: dict,
    sample_job: dict,
) -> None:
    """A researcher cannot accept a bid — expect 403."""
    bid_resp = _place_bid(client, sample_job["id"], researcher_headers)
    bid_id = bid_resp.json()["data"]["id"]

    resp = client.post(f"/api/v1/bids/{bid_id}/accept", headers=researcher_headers)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Rejecting bids
# ---------------------------------------------------------------------------

def test_reject_bid(
    client: TestClient,
    student_headers: dict,
    researcher_headers: dict,
    sample_job: dict,
) -> None:
    """A student can reject a pending bid; the bid status becomes 'rejected'."""
    bid_resp = _place_bid(client, sample_job["id"], researcher_headers)
    bid_id = bid_resp.json()["data"]["id"]

    reject_resp = client.post(
        f"/api/v1/bids/{bid_id}/reject",
        headers=student_headers,
    )
    assert reject_resp.status_code == 200
    assert reject_resp.json()["data"]["status"] == "rejected"


def test_reject_already_accepted_bid(
    client: TestClient,
    student_headers: dict,
    researcher_headers: dict,
    sample_job: dict,
) -> None:
    """Cannot reject a bid that has already been accepted — expect 400."""
    bid_resp = _place_bid(client, sample_job["id"], researcher_headers)
    bid_id = bid_resp.json()["data"]["id"]

    client.post(f"/api/v1/bids/{bid_id}/accept", headers=student_headers)

    resp = client.post(f"/api/v1/bids/{bid_id}/reject", headers=student_headers)
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Counter bids
# ---------------------------------------------------------------------------

def test_counter_bid(
    client: TestClient,
    student_headers: dict,
    researcher_headers: dict,
    sample_job: dict,
) -> None:
    """A student can counter a pending bid; bid status becomes 'countered'."""
    bid_resp = _place_bid(client, sample_job["id"], researcher_headers)
    bid_id = bid_resp.json()["data"]["id"]

    counter_resp = client.post(
        f"/api/v1/bids/{bid_id}/counter",
        json={
            "new_price": "100.00",
            "message": "We would like to negotiate a lower price for this research task.",
        },
        headers=student_headers,
    )
    assert counter_resp.status_code == 200
    data = counter_resp.json()["data"]
    assert "bid_id" in data
    assert str(data["bid_id"]) == bid_id


# ---------------------------------------------------------------------------
# Withdrawing bids
# ---------------------------------------------------------------------------

def test_withdraw_bid(
    client: TestClient,
    researcher_headers: dict,
    sample_job: dict,
) -> None:
    """A researcher can withdraw their own pending bid."""
    bid_resp = _place_bid(client, sample_job["id"], researcher_headers)
    bid_id = bid_resp.json()["data"]["id"]

    withdraw_resp = client.post(
        f"/api/v1/bids/{bid_id}/withdraw",
        headers=researcher_headers,
    )
    assert withdraw_resp.status_code == 200
    assert withdraw_resp.json()["data"]["status"] == "withdrawn"


def test_withdraw_bid_by_student_forbidden(
    client: TestClient,
    student_headers: dict,
    researcher_headers: dict,
    sample_job: dict,
) -> None:
    """A student cannot withdraw a researcher's bid — expect 403."""
    bid_resp = _place_bid(client, sample_job["id"], researcher_headers)
    bid_id = bid_resp.json()["data"]["id"]

    resp = client.post(f"/api/v1/bids/{bid_id}/withdraw", headers=student_headers)
    assert resp.status_code == 403


def test_withdraw_already_withdrawn_bid(
    client: TestClient,
    researcher_headers: dict,
    sample_job: dict,
) -> None:
    """Cannot withdraw a bid that has already been withdrawn — expect 400."""
    bid_resp = _place_bid(client, sample_job["id"], researcher_headers)
    bid_id = bid_resp.json()["data"]["id"]

    client.post(f"/api/v1/bids/{bid_id}/withdraw", headers=researcher_headers)
    resp = client.post(f"/api/v1/bids/{bid_id}/withdraw", headers=researcher_headers)
    assert resp.status_code == 400
