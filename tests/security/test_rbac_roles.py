"""
Security tests: RBAC role enforcement.

25 tests verifying that each endpoint enforces its required role.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_student_cannot_access_professor_profile_endpoint(
    client: TestClient, student_headers: dict
) -> None:
    resp = client.get("/api/v1/professor/profile", headers=student_headers)
    assert resp.status_code == 403


def test_researcher_cannot_access_professor_profile_endpoint(
    client: TestClient, researcher_headers: dict
) -> None:
    resp = client.get("/api/v1/professor/profile", headers=researcher_headers)
    assert resp.status_code == 403


def test_student_cannot_create_professor_profile(
    client: TestClient, student_headers: dict
) -> None:
    resp = client.post(
        "/api/v1/professor/profile",
        json={"bio": "I am a student pretending to be professor",
              "title": "Dr.", "department": "CS",
              "expertise_areas": [], "review_subjects": []},
        headers=student_headers,
    )
    assert resp.status_code == 403


def test_researcher_cannot_create_professor_profile(
    client: TestClient, researcher_headers: dict
) -> None:
    resp = client.post(
        "/api/v1/professor/profile",
        json={"bio": "Researcher pretending to be professor",
              "title": "Prof.", "department": "Math",
              "expertise_areas": [], "review_subjects": []},
        headers=researcher_headers,
    )
    assert resp.status_code == 403


def test_student_cannot_start_contract(
    client: TestClient, full_contract: dict, student_headers: dict
) -> None:
    contract_id = full_contract["contract_id"]
    resp = client.post(
        f"/api/v1/contracts/{contract_id}/start",
        headers=student_headers,
    )
    assert resp.status_code == 403


def test_researcher_cannot_accept_bid(
    client: TestClient, student_headers: dict, researcher_headers: dict
) -> None:
    # Create job and bid
    job_resp = client.post(
        "/api/v1/jobs",
        json={"title": "RBAC Test Job", "description": "Testing RBAC for bid acceptance.",
              "subject": "Math", "academic_level": "Masters",
              "proposed_price": "100.00", "deadline": "2099-12-31T00:00:00Z"},
        headers=student_headers,
    )
    job_id = job_resp.json()["data"]["id"]
    bid_resp = client.post(
        f"/api/v1/jobs/{job_id}/bids",
        json={"proposed_price": "90.00", "message": "Bid for RBAC test"},
        headers=researcher_headers,
    )
    bid_id = bid_resp.json()["data"]["id"]
    # Researcher tries to accept own bid
    resp = client.post(f"/api/v1/bids/{bid_id}/accept", headers=researcher_headers)
    assert resp.status_code == 403


def test_student_cannot_submit_work(
    client: TestClient, started_contract: dict, student_headers: dict
) -> None:
    contract_id = started_contract["contract_id"]
    resp = client.post(
        "/api/v1/submissions",
        json={"contract_id": contract_id, "submission_notes": "Student submitting — RBAC test"},
        headers=student_headers,
    )
    assert resp.status_code == 403


def test_researcher_cannot_approve_submission(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
) -> None:
    contract_id = started_contract["contract_id"]
    # Researcher submits work
    sub_resp = client.post(
        "/api/v1/submissions",
        json={"contract_id": contract_id, "submission_notes": "Work completed and ready for review"},
        headers=researcher_headers,
    )
    sub_id = sub_resp.json()["data"]["id"]
    # Researcher tries to approve own submission
    resp = client.post(f"/api/v1/submissions/{sub_id}/approve", headers=researcher_headers)
    assert resp.status_code == 403


def test_non_admin_cannot_access_admin_users_list(
    client: TestClient, student_headers: dict
) -> None:
    resp = client.get("/api/v1/admin/users", headers=student_headers)
    assert resp.status_code == 403


def test_professor_cannot_access_admin_endpoints(
    client: TestClient, approved_professor_headers: dict
) -> None:
    resp = client.get("/api/v1/admin/users", headers=approved_professor_headers)
    assert resp.status_code == 403


def test_researcher_cannot_access_admin_dashboard(
    client: TestClient, researcher_headers: dict
) -> None:
    resp = client.get("/api/v1/admin/dashboard", headers=researcher_headers)
    assert resp.status_code == 403


def test_unauthenticated_can_access_jobs_publicly(
    client: TestClient
) -> None:
    """Job listing is a public endpoint — no auth required."""
    resp = client.get("/api/v1/jobs")
    assert resp.status_code == 200


def test_unauthenticated_cannot_access_contracts(
    client: TestClient
) -> None:
    resp = client.get("/api/v1/contracts")
    assert resp.status_code == 401


def test_unauthenticated_cannot_access_wallet(
    client: TestClient
) -> None:
    resp = client.get("/api/v1/payments/wallet")
    assert resp.status_code == 401


def test_unauthenticated_cannot_access_admin(
    client: TestClient
) -> None:
    resp = client.get("/api/v1/admin/users")
    assert resp.status_code == 401


def test_admin_can_access_all_admin_endpoints(
    client: TestClient, admin_headers: dict
) -> None:
    resp = client.get("/api/v1/admin/users", headers=admin_headers)
    assert resp.status_code == 200
    resp2 = client.get("/api/v1/admin/jobs", headers=admin_headers)
    assert resp2.status_code == 200
    resp3 = client.get("/api/v1/admin/dashboard", headers=admin_headers)
    assert resp3.status_code == 200


def test_super_admin_can_access_admin_endpoints(
    client: TestClient, super_admin_headers: dict
) -> None:
    resp = client.get("/api/v1/admin/users", headers=super_admin_headers)
    assert resp.status_code == 200


def test_student_cannot_escrow(
    client: TestClient, student_headers: dict, researcher_headers: dict
) -> None:
    """Escrow is student-only — but a student CAN escrow their own contract."""
    # This test verifies researchers cannot escrow
    job_resp = client.post(
        "/api/v1/jobs",
        json={"title": "Escrow RBAC Job", "description": "RBAC test for escrow endpoint.",
              "subject": "CS", "academic_level": "Bachelors",
              "proposed_price": "100.00", "deadline": "2099-12-31T00:00:00Z"},
        headers=student_headers,
    )
    job_id = job_resp.json()["data"]["id"]
    bid_resp = client.post(
        f"/api/v1/jobs/{job_id}/bids",
        json={"proposed_price": "90.00", "message": "Escrow RBAC test bid"},
        headers=researcher_headers,
    )
    bid_id = bid_resp.json()["data"]["id"]
    accept_resp = client.post(f"/api/v1/bids/{bid_id}/accept", headers=student_headers)
    contract_id = accept_resp.json()["data"]["id"]

    # Researcher tries to escrow
    resp = client.post(
        "/api/v1/payments/escrow",
        json={"contract_id": contract_id, "payment_provider": "wallet", "provider_reference": "test"},
        headers=researcher_headers,
    )
    assert resp.status_code == 403


def test_student_cannot_request_payout(
    client: TestClient, student_headers: dict
) -> None:
    resp = client.post(
        "/api/v1/payments/payout",
        json={"amount": "50.00", "provider": "paypal"},
        headers=student_headers,
    )
    assert resp.status_code == 403


def test_student_cannot_view_professor_queue(
    client: TestClient, student_headers: dict
) -> None:
    resp = client.get("/api/v1/professor/queue", headers=student_headers)
    assert resp.status_code == 403


def test_student_cannot_submit_credential_review(
    client: TestClient, student_headers: dict
) -> None:
    """Only researchers can submit credentials for review."""
    resp = client.post(
        "/api/v1/professor/credentials",
        json={"credential_type": "phd", "institution_name": "MIT",
              "field_of_study": "CS"},
        headers=student_headers,
    )
    assert resp.status_code == 403


def test_researcher_cannot_verify_credential(
    client: TestClient,
    researcher_headers: dict,
) -> None:
    """Only professors can verify credentials."""
    import uuid
    fake_id = str(uuid.uuid4())
    resp = client.post(
        f"/api/v1/professor/credentials/{fake_id}/action",
        json={"action": "verify"},
        headers=researcher_headers,
    )
    assert resp.status_code == 403


def test_require_role_admin_elevates_super_admin(
    client: TestClient, super_admin_headers: dict
) -> None:
    """super_admin should be able to access admin-required endpoints."""
    resp = client.get("/api/v1/admin/users", headers=super_admin_headers)
    assert resp.status_code == 200


def test_student_cannot_access_admin_transactions(
    client: TestClient, student_headers: dict
) -> None:
    resp = client.get("/api/v1/admin/transactions", headers=student_headers)
    assert resp.status_code == 403


def test_student_cannot_release_payment_for_others_contract(
    client: TestClient,
    full_contract: dict,
    db,
) -> None:
    """A different student cannot release payment for someone else's contract."""
    import uuid
    email = f"stu2-{uuid.uuid4().hex[:8]}@test.com"
    client.post("/api/v1/auth/register", json={
        "email": email, "password": "TestPassword123!",
        "first_name": "Other", "last_name": "Student", "role": "student"
    })
    login = client.post("/api/v1/auth/login", json={"email": email, "password": "TestPassword123!"})
    other_student = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}

    contract_id = full_contract["contract_id"]
    resp = client.post(
        "/api/v1/payments/release",
        json={"contract_id": contract_id},
        headers=other_student,
    )
    assert resp.status_code == 403
