"""
Security tests: RBAC privilege escalation prevention.

20 tests verifying users cannot access or modify others' resources.
"""
from __future__ import annotations

import uuid
import pytest
from fastapi.testclient import TestClient


def _make_student(client, db):
    from app.models.user import User
    email = f"esc-stu-{uuid.uuid4().hex[:8]}@test.com"
    client.post("/api/v1/auth/register", json={
        "email": email, "password": "TestPassword123!",
        "first_name": "Other", "last_name": "Student", "role": "student"
    })
    login = client.post("/api/v1/auth/login", json={"email": email, "password": "TestPassword123!"})
    token = login.json()["data"]["access_token"]
    user = db.query(User).filter(User.email == email).first()
    return {"Authorization": f"Bearer {token}"}, str(user.id)


def _make_researcher(client, db):
    from app.models.user import User
    email = f"esc-res-{uuid.uuid4().hex[:8]}@test.com"
    client.post("/api/v1/auth/register", json={
        "email": email, "password": "TestPassword123!",
        "first_name": "Other", "last_name": "Researcher", "role": "researcher"
    })
    login = client.post("/api/v1/auth/login", json={"email": email, "password": "TestPassword123!"})
    token = login.json()["data"]["access_token"]
    user = db.query(User).filter(User.email == email).first()
    return {"Authorization": f"Bearer {token}"}, str(user.id)


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_student_cannot_upgrade_own_role_via_api(
    client: TestClient, student_headers: dict
) -> None:
    """No self-role assignment endpoint — auth/register only allows student/researcher."""
    # There's no user self-update role endpoint; admin role endpoint requires admin auth
    me = client.get("/api/v1/auth/me", headers=student_headers)
    user_id = me.json()["data"]["id"]

    # Try to access admin role endpoint without admin privileges
    resp = client.post(
        f"/api/v1/admin/users/{user_id}/role",
        json={"role": "admin"},
        headers=student_headers,
    )
    assert resp.status_code == 403


def test_researcher_cannot_approve_own_bid(
    client: TestClient, student_headers: dict, researcher_headers: dict
) -> None:
    job_resp = client.post(
        "/api/v1/jobs",
        json={"title": "Own Bid Job", "description": "Testing researcher approving own bid.",
              "subject": "Math", "academic_level": "Bachelors",
              "proposed_price": "100.00", "deadline": "2099-12-31T00:00:00Z"},
        headers=student_headers,
    )
    job_id = job_resp.json()["data"]["id"]
    bid_resp = client.post(
        f"/api/v1/jobs/{job_id}/bids",
        json={"proposed_price": "90.00", "message": "Own bid approval test"},
        headers=researcher_headers,
    )
    bid_id = bid_resp.json()["data"]["id"]
    resp = client.post(f"/api/v1/bids/{bid_id}/accept", headers=researcher_headers)
    assert resp.status_code == 403


def test_user_cannot_modify_another_users_job(
    client: TestClient, student_headers: dict, db
) -> None:
    # Create job with student
    job_resp = client.post(
        "/api/v1/jobs",
        json={"title": "Target Job", "description": "Job to test unauthorized modification.",
              "subject": "Physics", "academic_level": "Masters",
              "proposed_price": "200.00", "deadline": "2099-12-31T00:00:00Z"},
        headers=student_headers,
    )
    job_id = job_resp.json()["data"]["id"]

    # Another student tries to modify it
    other_headers, _ = _make_student(client, db)
    resp = client.patch(
        f"/api/v1/jobs/{job_id}",
        json={"title": "Hacked Title"},
        headers=other_headers,
    )
    assert resp.status_code == 403


def test_user_cannot_view_another_users_wallet(
    client: TestClient, student_headers: dict, db
) -> None:
    """Wallet is accessed via /payments/wallet for own user only."""
    # Student deposits to create wallet
    client.post(
        "/api/v1/payments/wallet/deposit",
        json={"amount": "100.00"},
        headers=student_headers,
    )
    # Another student can only view their own wallet
    other_headers, _ = _make_student(client, db)
    # GET /payments/wallet returns current user's wallet, not another's
    resp = client.get("/api/v1/payments/wallet", headers=other_headers)
    # Should get 404 (no wallet for other user) or own wallet
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        # Should not have balance from original student
        balance = float(resp.json()["data"]["balance"])
        assert balance == 0.0


def test_user_cannot_release_payment_for_others_contract(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    db,
) -> None:
    contract_id = started_contract["contract_id"]
    # Submit work
    client.post(
        "/api/v1/submissions",
        json={"contract_id": contract_id, "submission_notes": "Work completed and ready for review"},
        headers=researcher_headers,
    )
    # Another student tries to release
    other_headers, _ = _make_student(client, db)
    resp = client.post(
        "/api/v1/payments/release",
        json={"contract_id": contract_id},
        headers=other_headers,
    )
    assert resp.status_code == 403


def test_user_cannot_refund_others_contract(
    client: TestClient, full_contract: dict, db
) -> None:
    contract_id = full_contract["contract_id"]
    # Another student tries to refund
    other_headers, _ = _make_student(client, db)
    resp = client.post(
        "/api/v1/payments/refund",
        json={"contract_id": contract_id, "reason": "Unauthorized refund attempt"},
        headers=other_headers,
    )
    assert resp.status_code == 403


def test_researcher_cannot_accept_bid_on_others_job(
    client: TestClient, student_headers: dict, db
) -> None:
    # Create job and bid
    job_resp = client.post(
        "/api/v1/jobs",
        json={"title": "Unauthorized Accept Job", "description": "Job for unauthorized bid accept test.",
              "subject": "CS", "academic_level": "Bachelors",
              "proposed_price": "100.00", "deadline": "2099-12-31T00:00:00Z"},
        headers=student_headers,
    )
    job_id = job_resp.json()["data"]["id"]

    r1_headers, _ = _make_researcher(client, db)
    bid_resp = client.post(
        f"/api/v1/jobs/{job_id}/bids",
        json={"proposed_price": "90.00", "message": "Bid for unauthorized accept test"},
        headers=r1_headers,
    )
    bid_id = bid_resp.json()["data"]["id"]

    # Another student tries to accept bid
    other_student_headers, _ = _make_student(client, db)
    resp = client.post(f"/api/v1/bids/{bid_id}/accept", headers=other_student_headers)
    assert resp.status_code == 403


def test_cannot_view_another_users_submissions(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    db,
) -> None:
    contract_id = started_contract["contract_id"]
    sub_resp = client.post(
        "/api/v1/submissions",
        json={"contract_id": contract_id, "submission_notes": "Work completed and ready for review"},
        headers=researcher_headers,
    )
    sub_id = sub_resp.json()["data"]["id"]

    # Unrelated user tries to view submission
    other_headers, _ = _make_student(client, db)
    resp = client.get(f"/api/v1/submissions/{sub_id}", headers=other_headers)
    assert resp.status_code == 403


def test_non_admin_cannot_verify_user(
    client: TestClient, student_headers: dict, db
) -> None:
    other_headers, user_id = _make_student(client, db)
    resp = client.post(
        f"/api/v1/admin/users/{user_id}/verify",
        headers=student_headers,
    )
    assert resp.status_code == 403


def test_professor_cannot_ban_user(
    client: TestClient, approved_professor_headers: dict, db
) -> None:
    other_headers, user_id = _make_student(client, db)
    resp = client.post(
        f"/api/v1/admin/users/{user_id}/ban",
        json={"reason": "Professor trying to ban user — should fail"},
        headers=approved_professor_headers,
    )
    assert resp.status_code == 403


def test_student_cannot_withdraw_others_bid(
    client: TestClient, student_headers: dict, researcher_headers: dict, db
) -> None:
    job_resp = client.post(
        "/api/v1/jobs",
        json={"title": "Withdraw Bid Test", "description": "Testing unauthorized bid withdrawal.",
              "subject": "History", "academic_level": "Bachelors",
              "proposed_price": "80.00", "deadline": "2099-12-31T00:00:00Z"},
        headers=student_headers,
    )
    job_id = job_resp.json()["data"]["id"]
    bid_resp = client.post(
        f"/api/v1/jobs/{job_id}/bids",
        json={"proposed_price": "75.00", "message": "Bid to test withdrawal"},
        headers=researcher_headers,
    )
    bid_id = bid_resp.json()["data"]["id"]

    # Another researcher tries to withdraw
    other_headers, _ = _make_researcher(client, db)
    resp = client.post(f"/api/v1/bids/{bid_id}/withdraw", headers=other_headers)
    assert resp.status_code in (403, 404)


def test_student_cannot_start_contract(
    client: TestClient, full_contract: dict, student_headers: dict
) -> None:
    contract_id = full_contract["contract_id"]
    resp = client.post(
        f"/api/v1/contracts/{contract_id}/start",
        headers=student_headers,
    )
    assert resp.status_code == 403


def test_researcher_cannot_refund_contract(
    client: TestClient, full_contract: dict, researcher_headers: dict
) -> None:
    contract_id = full_contract["contract_id"]
    resp = client.post(
        "/api/v1/payments/refund",
        json={"contract_id": contract_id, "reason": "Researcher requesting refund"},
        headers=researcher_headers,
    )
    assert resp.status_code == 403


def test_third_party_cannot_view_contract_submissions(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    db,
) -> None:
    contract_id = started_contract["contract_id"]
    client.post(
        "/api/v1/submissions",
        json={"contract_id": contract_id, "submission_notes": "Work completed and ready for review"},
        headers=researcher_headers,
    )
    # Unrelated student
    other_headers, _ = _make_student(client, db)
    resp = client.get(
        f"/api/v1/contracts/{contract_id}/submissions",
        headers=other_headers,
    )
    assert resp.status_code == 403


def test_admin_can_be_set_only_by_super_admin(
    client: TestClient, admin_headers: dict, db
) -> None:
    _, user_id = _make_student(client, db)
    resp = client.post(
        f"/api/v1/admin/users/{user_id}/role",
        json={"role": "admin"},
        headers=admin_headers,
    )
    assert resp.status_code == 403


def test_researcher_cannot_list_admin_jobs(
    client: TestClient, researcher_headers: dict
) -> None:
    resp = client.get("/api/v1/admin/jobs", headers=researcher_headers)
    assert resp.status_code == 403


def test_student_cannot_list_admin_payouts(
    client: TestClient, student_headers: dict
) -> None:
    resp = client.get("/api/v1/admin/payouts", headers=student_headers)
    assert resp.status_code == 403


def test_student_cannot_access_admin_disputes(
    client: TestClient, student_headers: dict
) -> None:
    resp = client.get("/api/v1/admin/disputes", headers=student_headers)
    assert resp.status_code == 403


def test_super_admin_can_assign_admin_role(
    client: TestClient, super_admin_headers: dict, db
) -> None:
    _, user_id = _make_student(client, db)
    resp = client.post(
        f"/api/v1/admin/users/{user_id}/role",
        json={"role": "admin", "reason": "Promoting to admin for testing purposes"},
        headers=super_admin_headers,
    )
    assert resp.status_code == 200
    assert "admin" in resp.json()["data"]["message"]
