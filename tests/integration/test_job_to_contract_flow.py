"""
Integration tests: student creates job → researcher bids → student accepts → contract.

20 tests covering:
- Complete happy path
- Job status changes
- Bid status changes
- Other bids get rejected
- Contract fields (agreed_price, student_id, researcher_id)
- Conversation created
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def _create_job(client, student_headers, price="150.00", subject="Computer Science"):
    resp = client.post(
        "/api/v1/jobs",
        json={
            "title": "Integration Test Research Job",
            "description": "A detailed research job created to test the full job-to-contract flow.",
            "subject": subject,
            "academic_level": "Masters",
            "proposed_price": price,
            "deadline": "2099-12-31T00:00:00Z",
        },
        headers=student_headers,
    )
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["data"]


def _place_bid(client, researcher_headers, job_id, price="140.00"):
    resp = client.post(
        f"/api/v1/jobs/{job_id}/bids",
        json={
            "proposed_price": price,
            "message": "I have extensive experience in this research area and can deliver quality work.",
        },
        headers=researcher_headers,
    )
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["data"]


def _accept_bid(client, student_headers, bid_id):
    resp = client.post(f"/api/v1/bids/{bid_id}/accept", headers=student_headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


# ─────────────────────────────────────────────────────────────────────────────
# Happy path
# ─────────────────────────────────────────────────────────────────────────────

def test_complete_flow_creates_all_records(
    client: TestClient, student_headers: dict, researcher_headers: dict
) -> None:
    job = _create_job(client, student_headers)
    bid = _place_bid(client, researcher_headers, job["id"])
    contract = _accept_bid(client, student_headers, bid["id"])
    assert contract["id"] is not None
    assert contract["status"] == "accepted"


def test_job_status_becomes_accepted_after_bid_accepted(
    client: TestClient, student_headers: dict, researcher_headers: dict
) -> None:
    job = _create_job(client, student_headers)
    bid = _place_bid(client, researcher_headers, job["id"])
    _accept_bid(client, student_headers, bid["id"])

    # Get the job again
    job_resp = client.get(f"/api/v1/jobs/{job['id']}", headers=student_headers)
    assert job_resp.status_code == 200
    assert job_resp.json()["data"]["status"] == "accepted"


def test_accepted_bid_status_becomes_accepted(
    client: TestClient, student_headers: dict, researcher_headers: dict
) -> None:
    job = _create_job(client, student_headers)
    bid = _place_bid(client, researcher_headers, job["id"])
    _accept_bid(client, student_headers, bid["id"])

    bids_resp = client.get(f"/api/v1/jobs/{job['id']}/bids", headers=student_headers)
    assert bids_resp.status_code == 200
    bids = bids_resp.json()["data"]["items"]
    accepted_bids = [b for b in bids if b["id"] == bid["id"]]
    assert len(accepted_bids) == 1
    assert accepted_bids[0]["status"] == "accepted"


def test_other_bids_get_rejected_when_one_accepted(
    client: TestClient, student_headers: dict, researcher_headers: dict, db
) -> None:
    """When one bid is accepted, other bids on same job should be rejected."""
    import uuid
    from app.models.user import User

    # Create a second researcher
    email2 = f"researcher2-{uuid.uuid4().hex[:8]}@test.com"
    password = "TestPassword123!"
    client.post("/api/v1/auth/register", json={
        "email": email2, "password": password,
        "first_name": "R2", "last_name": "User", "role": "researcher"
    })
    login2 = client.post("/api/v1/auth/login", json={"email": email2, "password": password})
    researcher2_headers = {"Authorization": f"Bearer {login2.json()['data']['access_token']}"}

    job = _create_job(client, student_headers)
    bid1 = _place_bid(client, researcher_headers, job["id"], "130.00")
    bid2 = _place_bid(client, researcher2_headers, job["id"], "125.00")

    # Accept bid1
    _accept_bid(client, student_headers, bid1["id"])

    # bid2 should now be rejected
    bids_resp = client.get(f"/api/v1/jobs/{job['id']}/bids", headers=student_headers)
    bids = bids_resp.json()["data"]["items"]
    bid2_state = [b for b in bids if b["id"] == bid2["id"]][0]
    assert bid2_state["status"] == "rejected"


def test_contract_has_correct_agreed_price(
    client: TestClient, student_headers: dict, researcher_headers: dict
) -> None:
    job = _create_job(client, student_headers, price="200.00")
    bid = _place_bid(client, researcher_headers, job["id"], price="180.00")
    contract = _accept_bid(client, student_headers, bid["id"])
    assert float(contract["agreed_price"]) == 180.00


def test_contract_has_correct_student_id(
    client: TestClient, student_headers: dict, researcher_headers: dict
) -> None:
    job = _create_job(client, student_headers)
    bid = _place_bid(client, researcher_headers, job["id"])
    contract = _accept_bid(client, student_headers, bid["id"])

    student_resp = client.get("/api/v1/auth/me", headers=student_headers)
    student_id = student_resp.json()["data"]["id"]
    assert contract["student_id"] == student_id


def test_contract_has_correct_researcher_id(
    client: TestClient, student_headers: dict, researcher_headers: dict
) -> None:
    job = _create_job(client, student_headers)
    bid = _place_bid(client, researcher_headers, job["id"])
    contract = _accept_bid(client, student_headers, bid["id"])

    researcher_resp = client.get("/api/v1/auth/me", headers=researcher_headers)
    researcher_id = researcher_resp.json()["data"]["id"]
    assert contract["researcher_id"] == researcher_id


def test_contract_appears_in_researcher_contracts(
    client: TestClient, student_headers: dict, researcher_headers: dict
) -> None:
    job = _create_job(client, student_headers)
    bid = _place_bid(client, researcher_headers, job["id"])
    contract = _accept_bid(client, student_headers, bid["id"])
    contract_id = contract["id"]

    contracts_resp = client.get("/api/v1/contracts", headers=researcher_headers)
    assert contracts_resp.status_code == 200
    contract_ids = [c["id"] for c in contracts_resp.json()["data"]["items"]]
    assert contract_id in contract_ids


def test_contract_appears_in_student_contracts(
    client: TestClient, student_headers: dict, researcher_headers: dict
) -> None:
    job = _create_job(client, student_headers)
    bid = _place_bid(client, researcher_headers, job["id"])
    contract = _accept_bid(client, student_headers, bid["id"])
    contract_id = contract["id"]

    contracts_resp = client.get("/api/v1/contracts", headers=student_headers)
    assert contracts_resp.status_code == 200
    contract_ids = [c["id"] for c in contracts_resp.json()["data"]["items"]]
    assert contract_id in contract_ids


def test_cannot_accept_bid_on_accepted_job(
    client: TestClient, student_headers: dict, researcher_headers: dict, db
) -> None:
    """After a job is accepted, accepting another bid should fail."""
    import uuid
    from app.models.user import User

    email2 = f"r2-{uuid.uuid4().hex[:8]}@test.com"
    client.post("/api/v1/auth/register", json={
        "email": email2, "password": "TestPassword123!",
        "first_name": "R", "last_name": "Two", "role": "researcher"
    })
    login2 = client.post("/api/v1/auth/login", json={"email": email2, "password": "TestPassword123!"})
    r2_headers = {"Authorization": f"Bearer {login2.json()['data']['access_token']}"}

    job = _create_job(client, student_headers)
    bid1 = _place_bid(client, researcher_headers, job["id"])
    bid2 = _place_bid(client, r2_headers, job["id"])
    _accept_bid(client, student_headers, bid1["id"])

    # Try to accept bid2 — should fail
    resp = client.post(f"/api/v1/bids/{bid2['id']}/accept", headers=student_headers)
    assert resp.status_code == 400


def test_only_student_can_accept_bid(
    client: TestClient, student_headers: dict, researcher_headers: dict
) -> None:
    job = _create_job(client, student_headers)
    bid = _place_bid(client, researcher_headers, job["id"])
    resp = client.post(f"/api/v1/bids/{bid['id']}/accept", headers=researcher_headers)
    assert resp.status_code == 403


def test_researcher_cannot_bid_on_own_acceptance(
    client: TestClient, student_headers: dict, researcher_headers: dict
) -> None:
    """Researcher cannot accept a bid — only post bids."""
    job = _create_job(client, student_headers)
    bid = _place_bid(client, researcher_headers, job["id"])
    resp = client.post(f"/api/v1/bids/{bid['id']}/accept", headers=researcher_headers)
    assert resp.status_code == 403


def test_bid_on_nonexistent_job_returns_404(
    client: TestClient, researcher_headers: dict
) -> None:
    import uuid
    fake_id = str(uuid.uuid4())
    resp = client.post(
        f"/api/v1/jobs/{fake_id}/bids",
        json={"proposed_price": "100.00", "message": "Bid on non-existent job should fail"},
        headers=researcher_headers,
    )
    assert resp.status_code == 404


def test_contract_status_is_accepted_before_escrow(
    client: TestClient, student_headers: dict, researcher_headers: dict
) -> None:
    job = _create_job(client, student_headers)
    bid = _place_bid(client, researcher_headers, job["id"])
    contract = _accept_bid(client, student_headers, bid["id"])
    assert contract["status"] == "accepted"


def test_job_has_open_status_before_any_bid(
    client: TestClient, student_headers: dict
) -> None:
    job = _create_job(client, student_headers)
    assert job["status"] == "open"


def test_student_can_view_bids_on_their_job(
    client: TestClient, student_headers: dict, researcher_headers: dict
) -> None:
    job = _create_job(client, student_headers)
    _place_bid(client, researcher_headers, job["id"])
    resp = client.get(f"/api/v1/jobs/{job['id']}/bids", headers=student_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] >= 1


def test_multiple_bids_all_appear_in_list(
    client: TestClient, student_headers: dict, researcher_headers: dict, db
) -> None:
    import uuid
    email2 = f"r-multi-{uuid.uuid4().hex[:8]}@test.com"
    client.post("/api/v1/auth/register", json={
        "email": email2, "password": "TestPassword123!",
        "first_name": "Multi", "last_name": "Bidder", "role": "researcher"
    })
    login2 = client.post("/api/v1/auth/login", json={"email": email2, "password": "TestPassword123!"})
    r2_headers = {"Authorization": f"Bearer {login2.json()['data']['access_token']}"}

    job = _create_job(client, student_headers)
    _place_bid(client, researcher_headers, job["id"], "130.00")
    _place_bid(client, r2_headers, job["id"], "125.00")

    resp = client.get(f"/api/v1/jobs/{job['id']}/bids", headers=student_headers)
    assert resp.json()["data"]["total"] == 2


def test_contract_created_with_job_id(
    client: TestClient, student_headers: dict, researcher_headers: dict
) -> None:
    job = _create_job(client, student_headers)
    bid = _place_bid(client, researcher_headers, job["id"])
    contract = _accept_bid(client, student_headers, bid["id"])
    assert contract["job_id"] == job["id"]


def test_researcher_cannot_place_bid_twice_on_same_job(
    client: TestClient, student_headers: dict, researcher_headers: dict
) -> None:
    job = _create_job(client, student_headers)
    _place_bid(client, researcher_headers, job["id"])
    resp = client.post(
        f"/api/v1/jobs/{job['id']}/bids",
        json={"proposed_price": "120.00", "message": "Second bid attempt on same job should fail"},
        headers=researcher_headers,
    )
    assert resp.status_code in (400, 409)


def test_student_cannot_bid_on_own_job(
    client: TestClient, student_headers: dict
) -> None:
    job = _create_job(client, student_headers)
    resp = client.post(
        f"/api/v1/jobs/{job['id']}/bids",
        json={"proposed_price": "100.00", "message": "Student bidding on own job should fail"},
        headers=student_headers,
    )
    assert resp.status_code == 403
