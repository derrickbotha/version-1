"""
Dispute assignment and payout management API tests.

20 tests covering:
- Admin assigns professor to dispute
- Admin resolves dispute (various outcomes)
- Non-admin cannot resolve
- Non-existent dispute → 404
- Payout management (approve, reject, list)
"""
from __future__ import annotations

import uuid
import pytest
from fastapi.testclient import TestClient


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _open_dispute(client, started_contract, student_headers) -> str:
    """Open a dispute on a started contract, return dispute_id."""
    contract_id = started_contract["contract_id"]
    resp = client.post(
        "/api/v1/disputes",
        json={"contract_id": contract_id, "reason": "Work quality is poor and not meeting standards"},
        headers=student_headers,
    )
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["data"]["id"]


def _create_approved_professor(client, admin_headers, db) -> str:
    """Create an approved professor, return professor_profile_id."""
    from app.models.user import User
    email = f"prof-disp-{uuid.uuid4().hex[:8]}@test.com"
    password = "TestPassword123!"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password,
              "first_name": "Dispute", "last_name": "Prof", "role": "student"},
    )
    user = db.query(User).filter(User.email == email).first()
    user.role = "professor"
    db.commit()
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    token = login.json()["data"]["access_token"]
    prof_headers = {"Authorization": f"Bearer {token}"}
    prof_resp = client.post(
        "/api/v1/professor/profile",
        json={"bio": "Expert", "title": "Dr.", "department": "CS",
              "expertise_areas": ["AI"], "review_subjects": ["Mathematics"]},
        headers=prof_headers,
    )
    assert prof_resp.status_code in (200, 201), prof_resp.text
    profile_id = prof_resp.json()["id"]
    client.post(
        f"/api/v1/admin/professors/{profile_id}/action",
        json={"action": "approve"},
        headers=admin_headers,
    )
    return profile_id


def _create_researcher_payout(client, researcher_headers, started_contract, student_headers) -> str:
    """Create a scenario where researcher has funds and requests payout. Returns payout_id."""
    contract_id = started_contract["contract_id"]
    # Submit work
    client.post(
        "/api/v1/submissions",
        json={"contract_id": contract_id, "submission_notes": "Completed work"},
        headers=researcher_headers,
    )
    # Approve submission
    subs = client.get(f"/api/v1/contracts/{contract_id}/submissions", headers=student_headers)
    sub_id = subs.json()["data"]["items"][0]["id"]
    client.post(f"/api/v1/submissions/{sub_id}/approve", headers=student_headers)
    # Release payment
    client.post(
        "/api/v1/payments/release",
        json={"contract_id": contract_id},
        headers=student_headers,
    )
    # Request payout
    payout_resp = client.post(
        "/api/v1/payments/payout",
        json={"amount": "100.00", "provider": "paypal"},
        headers=researcher_headers,
    )
    assert payout_resp.status_code in (200, 201), payout_resp.text
    return payout_resp.json()["data"]["id"]


# ─────────────────────────────────────────────────────────────────────────────
# Dispute assignment
# ─────────────────────────────────────────────────────────────────────────────

def test_admin_can_assign_professor_to_dispute(
    client: TestClient,
    admin_headers: dict,
    started_contract: dict,
    student_headers: dict,
    db,
) -> None:
    dispute_id = _open_dispute(client, started_contract, student_headers)
    professor_profile_id = _create_approved_professor(client, admin_headers, db)
    resp = client.post(
        f"/api/v1/admin/disputes/{dispute_id}/assign-professor",
        json={"professor_id": professor_profile_id},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "queue_item_id" in data
    assert "professor_id" in data


def test_admin_assign_professor_creates_queue_item(
    client: TestClient,
    admin_headers: dict,
    started_contract: dict,
    student_headers: dict,
    approved_professor_headers: dict,
    db,
) -> None:
    dispute_id = _open_dispute(client, started_contract, student_headers)
    professor_profile_id = _create_approved_professor(client, admin_headers, db)
    resp = client.post(
        f"/api/v1/admin/disputes/{dispute_id}/assign-professor",
        json={"professor_id": professor_profile_id, "notes": "Please review this urgent dispute"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["queue_item_id"] is not None


def test_admin_resolve_dispute_refund_student(
    client: TestClient,
    admin_headers: dict,
    started_contract: dict,
    student_headers: dict,
) -> None:
    dispute_id = _open_dispute(client, started_contract, student_headers)
    resp = client.post(
        f"/api/v1/admin/disputes/{dispute_id}/resolve",
        json={
            "resolution": "Student's complaint is valid. Work does not meet required standards.",
            "financial_action": "full_refund",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "resolved"


def test_admin_resolve_dispute_release_researcher(
    client: TestClient,
    admin_headers: dict,
    started_contract: dict,
    student_headers: dict,
) -> None:
    dispute_id = _open_dispute(client, started_contract, student_headers)
    resp = client.post(
        f"/api/v1/admin/disputes/{dispute_id}/resolve",
        json={
            "resolution": "Researcher completed work to acceptable standard per contract terms.",
            "financial_action": "full_release",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "resolved"


def test_non_admin_cannot_resolve_dispute(
    client: TestClient,
    student_headers: dict,
    started_contract: dict,
) -> None:
    dispute_id = _open_dispute(client, started_contract, student_headers)
    resp = client.post(
        f"/api/v1/admin/disputes/{dispute_id}/resolve",
        json={
            "resolution": "Student trying to resolve own dispute — should fail.",
            "financial_action": "full_refund",
        },
        headers=student_headers,
    )
    assert resp.status_code == 403


def test_resolve_nonexistent_dispute_returns_404(
    client: TestClient, admin_headers: dict
) -> None:
    fake_id = str(uuid.uuid4())
    resp = client.post(
        f"/api/v1/admin/disputes/{fake_id}/resolve",
        json={
            "resolution": "This dispute does not exist and should return a not found error.",
            "financial_action": "full_refund",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 404


def test_admin_can_list_all_disputes(
    client: TestClient,
    admin_headers: dict,
    started_contract: dict,
    student_headers: dict,
) -> None:
    _open_dispute(client, started_contract, student_headers)
    resp = client.get("/api/v1/admin/disputes", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


def test_admin_disputes_list_non_admin_forbidden(
    client: TestClient, researcher_headers: dict
) -> None:
    resp = client.get("/api/v1/admin/disputes", headers=researcher_headers)
    assert resp.status_code == 403


def test_resolve_already_resolved_dispute_returns_409(
    client: TestClient,
    admin_headers: dict,
    started_contract: dict,
    student_headers: dict,
) -> None:
    dispute_id = _open_dispute(client, started_contract, student_headers)
    # First resolution
    client.post(
        f"/api/v1/admin/disputes/{dispute_id}/resolve",
        json={"resolution": "First resolution — student is correct and work is not adequate.",
              "financial_action": "full_refund"},
        headers=admin_headers,
    )
    # Second resolution should fail
    resp = client.post(
        f"/api/v1/admin/disputes/{dispute_id}/resolve",
        json={"resolution": "Second resolution attempt — should fail with conflict error.",
              "financial_action": "full_release"},
        headers=admin_headers,
    )
    assert resp.status_code == 409


# ─────────────────────────────────────────────────────────────────────────────
# Payout management
# ─────────────────────────────────────────────────────────────────────────────

def test_payout_list_shows_pending_payouts(
    client: TestClient,
    admin_headers: dict,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
) -> None:
    _create_researcher_payout(client, researcher_headers, started_contract, student_headers)
    resp = client.get("/api/v1/admin/payouts", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] >= 1


def test_admin_can_approve_payout(
    client: TestClient,
    admin_headers: dict,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
) -> None:
    payout_id = _create_researcher_payout(client, researcher_headers, started_contract, student_headers)
    resp = client.post(
        f"/api/v1/admin/payouts/{payout_id}/approve",
        json={"notes": "Approved after verification"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "processing"


def test_after_payout_approval_status_is_processing(
    client: TestClient,
    admin_headers: dict,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
) -> None:
    payout_id = _create_researcher_payout(client, researcher_headers, started_contract, student_headers)
    client.post(
        f"/api/v1/admin/payouts/{payout_id}/approve",
        json={},
        headers=admin_headers,
    )
    # List payouts and verify status
    resp = client.get("/api/v1/admin/payouts?status_filter=processing", headers=admin_headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    payout_ids = [p["id"] for p in items]
    assert payout_id in payout_ids


def test_admin_can_reject_payout_with_reason(
    client: TestClient,
    admin_headers: dict,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
) -> None:
    payout_id = _create_researcher_payout(client, researcher_headers, started_contract, student_headers)
    resp = client.post(
        f"/api/v1/admin/payouts/{payout_id}/reject",
        json={"reason": "Invalid account details provided"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "failed"


def test_non_admin_cannot_approve_payout(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
) -> None:
    payout_id = _create_researcher_payout(client, researcher_headers, started_contract, student_headers)
    resp = client.post(
        f"/api/v1/admin/payouts/{payout_id}/approve",
        json={},
        headers=researcher_headers,
    )
    assert resp.status_code == 403


def test_approve_nonexistent_payout_returns_404(
    client: TestClient, admin_headers: dict
) -> None:
    fake_id = str(uuid.uuid4())
    resp = client.post(
        f"/api/v1/admin/payouts/{fake_id}/approve",
        json={},
        headers=admin_headers,
    )
    assert resp.status_code == 404


def test_admin_payout_list_filtered_by_status(
    client: TestClient,
    admin_headers: dict,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
) -> None:
    _create_researcher_payout(client, researcher_headers, started_contract, student_headers)
    resp = client.get("/api/v1/admin/payouts?status_filter=pending", headers=admin_headers)
    assert resp.status_code == 200
    for item in resp.json()["data"]["items"]:
        assert item["status"] == "pending"


def test_reject_payout_reason_too_short_returns_422(
    client: TestClient,
    admin_headers: dict,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
) -> None:
    payout_id = _create_researcher_payout(client, researcher_headers, started_contract, student_headers)
    resp = client.post(
        f"/api/v1/admin/payouts/{payout_id}/reject",
        json={"reason": "Bad"},  # Too short (min_length=10)
        headers=admin_headers,
    )
    assert resp.status_code == 422
