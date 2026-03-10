"""
Tests for the bids API endpoints.

POST /api/v1/jobs/{id}/bids
GET  /api/v1/jobs/{id}/bids
POST /api/v1/bids/{id}/accept
POST /api/v1/bids/{id}/reject
POST /api/v1/bids/{id}/counter
POST /api/v1/bids/{id}/withdraw
GET  /api/v1/bids/mine
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient


JOB_PAYLOAD = {
    "title": "Bids API Test Job",
    "description": "A job used for testing bid-related endpoints.",
    "subject": "Economics",
    "academic_level": "Masters",
    "proposed_price": "200.00",
    "deadline": "2099-12-31T23:59:59Z",
}

BID_PAYLOAD = {
    "proposed_price": "180.00",
    "message": "I am highly qualified to complete this research task.",
}


def _create_job(client, headers):
    resp = client.post("/api/v1/jobs", json=JOB_PAYLOAD, headers=headers)
    assert resp.status_code in (200, 201)
    return resp.json()["data"]


def _place_bid(client, job_id, headers, payload=None):
    payload = payload or BID_PAYLOAD
    resp = client.post(f"/api/v1/jobs/{job_id}/bids", json=payload, headers=headers)
    assert resp.status_code in (200, 201), f"Bid failed: {resp.text}"
    return resp.json()["data"]


# ---------------------------------------------------------------------------
# Placing bids
# ---------------------------------------------------------------------------

def test_researcher_can_place_bid(client, student_headers, researcher_headers):
    """Researcher can place a bid on an open job, returns 201."""
    job = _create_job(client, student_headers)
    resp = client.post(f"/api/v1/jobs/{job['id']}/bids", json=BID_PAYLOAD, headers=researcher_headers)
    assert resp.status_code in (200, 201)


def test_place_bid_returns_bid_data(client, student_headers, researcher_headers):
    """Placed bid response contains required fields."""
    job = _create_job(client, student_headers)
    resp = client.post(f"/api/v1/jobs/{job['id']}/bids", json=BID_PAYLOAD, headers=researcher_headers)
    data = resp.json()["data"]
    assert "id" in data
    assert "proposed_price" in data
    assert data["status"] == "pending"


def test_student_cannot_place_bid(client, student_headers):
    """Student cannot place a bid (403)."""
    job = _create_job(client, student_headers)
    resp = client.post(f"/api/v1/jobs/{job['id']}/bids", json=BID_PAYLOAD, headers=student_headers)
    assert resp.status_code == 403


def test_unauthenticated_cannot_place_bid(client, student_headers):
    """Unauthenticated user cannot place a bid (401)."""
    job = _create_job(client, student_headers)
    resp = client.post(f"/api/v1/jobs/{job['id']}/bids", json=BID_PAYLOAD)
    assert resp.status_code == 401


def test_cannot_bid_on_nonexistent_job(client, researcher_headers):
    """Bidding on a non-existent job returns 404."""
    resp = client.post(f"/api/v1/jobs/{uuid.uuid4()}/bids", json=BID_PAYLOAD, headers=researcher_headers)
    assert resp.status_code == 404


def test_cannot_place_duplicate_active_bid(client, student_headers, researcher_headers):
    """Researcher cannot place a duplicate active bid on the same job."""
    job = _create_job(client, student_headers)
    client.post(f"/api/v1/jobs/{job['id']}/bids", json=BID_PAYLOAD, headers=researcher_headers)
    resp = client.post(f"/api/v1/jobs/{job['id']}/bids", json=BID_PAYLOAD, headers=researcher_headers)
    assert resp.status_code in (400, 409)


# ---------------------------------------------------------------------------
# Listing bids
# ---------------------------------------------------------------------------

def test_student_can_list_bids_on_own_job(client, student_headers, researcher_headers):
    """Student can list bids on their own job."""
    job = _create_job(client, student_headers)
    _place_bid(client, job["id"], researcher_headers)
    resp = client.get(f"/api/v1/jobs/{job['id']}/bids", headers=student_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] >= 1


def test_researcher_cannot_list_all_bids_on_job(client, student_headers, researcher_headers):
    """Researcher cannot list all bids on a job (only student or admin can)."""
    job = _create_job(client, student_headers)
    _place_bid(client, job["id"], researcher_headers)
    resp = client.get(f"/api/v1/jobs/{job['id']}/bids", headers=researcher_headers)
    assert resp.status_code == 403


def test_unauthenticated_cannot_list_bids(client, student_headers, researcher_headers):
    """Unauthenticated user cannot list bids."""
    job = _create_job(client, student_headers)
    _place_bid(client, job["id"], researcher_headers)
    resp = client.get(f"/api/v1/jobs/{job['id']}/bids")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Accept bid
# ---------------------------------------------------------------------------

def test_student_can_accept_bid(client, student_headers, researcher_headers):
    """Student can accept a bid, creating a contract."""
    job = _create_job(client, student_headers)
    bid = _place_bid(client, job["id"], researcher_headers)
    resp = client.post(f"/api/v1/bids/{bid['id']}/accept", headers=student_headers)
    assert resp.status_code == 200


def test_accept_bid_creates_contract(client, student_headers, researcher_headers):
    """Accepting a bid creates a contract and returns contract data."""
    job = _create_job(client, student_headers)
    bid = _place_bid(client, job["id"], researcher_headers)
    resp = client.post(f"/api/v1/bids/{bid['id']}/accept", headers=student_headers)
    data = resp.json()["data"]
    assert "id" in data
    assert data["status"] == "accepted"


def test_accept_bid_rejects_other_bids(client, student_headers, db):
    """Accepting one bid should reject other bids on the same job."""
    from tests.conftest import auth_headers
    researcher2_headers = auth_headers(client, "researcher")
    job = _create_job(client, student_headers)

    from tests.conftest import auth_headers as ah
    researcher_h = ah(client, "researcher")
    bid1 = _place_bid(client, job["id"], researcher_h)
    bid2 = _place_bid(client, job["id"], researcher2_headers)

    # Accept bid1
    client.post(f"/api/v1/bids/{bid1['id']}/accept", headers=student_headers)

    # bid2 should now be rejected
    resp = client.get(f"/api/v1/bids/mine", headers=researcher2_headers)
    assert resp.status_code == 200
    bids = resp.json()["data"]["items"]
    rejected = [b for b in bids if b["id"] == bid2["id"]]
    if rejected:
        assert rejected[0]["status"] == "rejected"


def test_cannot_accept_already_accepted_bid(client, student_headers, researcher_headers):
    """Cannot accept a bid that was already accepted (400)."""
    job = _create_job(client, student_headers)
    bid = _place_bid(client, job["id"], researcher_headers)
    client.post(f"/api/v1/bids/{bid['id']}/accept", headers=student_headers)
    resp = client.post(f"/api/v1/bids/{bid['id']}/accept", headers=student_headers)
    assert resp.status_code in (400, 409)


def test_student_cannot_accept_bid_on_another_students_job(client, student_headers, researcher_headers, db):
    """Student cannot accept a bid on another student's job."""
    from tests.conftest import auth_headers
    student2_headers = auth_headers(client, "student")
    job = _create_job(client, student_headers)
    bid = _place_bid(client, job["id"], researcher_headers)
    resp = client.post(f"/api/v1/bids/{bid['id']}/accept", headers=student2_headers)
    assert resp.status_code == 403


def test_researcher_cannot_accept_bid(client, student_headers, researcher_headers):
    """Researcher cannot accept a bid (only student can)."""
    job = _create_job(client, student_headers)
    bid = _place_bid(client, job["id"], researcher_headers)
    resp = client.post(f"/api/v1/bids/{bid['id']}/accept", headers=researcher_headers)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Reject bid
# ---------------------------------------------------------------------------

def test_student_can_reject_bid(client, student_headers, researcher_headers):
    """Student can reject a bid."""
    job = _create_job(client, student_headers)
    bid = _place_bid(client, job["id"], researcher_headers)
    resp = client.post(f"/api/v1/bids/{bid['id']}/reject", headers=student_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "rejected"


def test_researcher_cannot_reject_bid(client, student_headers, researcher_headers):
    """Researcher cannot reject a bid (only student can)."""
    job = _create_job(client, student_headers)
    bid = _place_bid(client, job["id"], researcher_headers)
    resp = client.post(f"/api/v1/bids/{bid['id']}/reject", headers=researcher_headers)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Counter bid
# ---------------------------------------------------------------------------

def test_student_can_counter_bid(client, student_headers, researcher_headers):
    """Student can submit a counter-offer on a bid."""
    job = _create_job(client, student_headers)
    bid = _place_bid(client, job["id"], researcher_headers)
    resp = client.post(
        f"/api/v1/bids/{bid['id']}/counter",
        json={"new_price": "160.00", "message": "Can you do it for 160?"},
        headers=student_headers,
    )
    assert resp.status_code == 200


def test_researcher_cannot_counter_bid(client, student_headers, researcher_headers):
    """Researcher cannot submit a counter-offer (only student can)."""
    job = _create_job(client, student_headers)
    bid = _place_bid(client, job["id"], researcher_headers)
    resp = client.post(
        f"/api/v1/bids/{bid['id']}/counter",
        json={"new_price": "160.00", "message": "Counter"},
        headers=researcher_headers,
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Withdraw bid
# ---------------------------------------------------------------------------

def test_researcher_can_withdraw_bid(client, student_headers, researcher_headers):
    """Researcher can withdraw their own bid."""
    job = _create_job(client, student_headers)
    bid = _place_bid(client, job["id"], researcher_headers)
    resp = client.post(f"/api/v1/bids/{bid['id']}/withdraw", headers=researcher_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "withdrawn"


def test_withdrawn_bid_cannot_be_accepted(client, student_headers, researcher_headers):
    """A withdrawn bid cannot be accepted."""
    job = _create_job(client, student_headers)
    bid = _place_bid(client, job["id"], researcher_headers)
    client.post(f"/api/v1/bids/{bid['id']}/withdraw", headers=researcher_headers)
    resp = client.post(f"/api/v1/bids/{bid['id']}/accept", headers=student_headers)
    assert resp.status_code in (400, 409)


def test_student_cannot_withdraw_bid(client, student_headers, researcher_headers):
    """Student cannot withdraw a bid (only researcher can)."""
    job = _create_job(client, student_headers)
    bid = _place_bid(client, job["id"], researcher_headers)
    resp = client.post(f"/api/v1/bids/{bid['id']}/withdraw", headers=student_headers)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Get my bids (researcher)
# ---------------------------------------------------------------------------

def test_researcher_can_view_own_bids(client, student_headers, researcher_headers):
    """Researcher can view their own bids."""
    job = _create_job(client, student_headers)
    _place_bid(client, job["id"], researcher_headers)
    resp = client.get("/api/v1/bids/mine", headers=researcher_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] >= 1


def test_student_cannot_view_researcher_bids(client, student_headers):
    """Student cannot access GET /bids/mine (requires researcher role)."""
    resp = client.get("/api/v1/bids/mine", headers=student_headers)
    assert resp.status_code == 403


def test_unauthenticated_cannot_view_mine_bids(client):
    """Unauthenticated cannot access GET /bids/mine."""
    resp = client.get("/api/v1/bids/mine")
    assert resp.status_code == 401
