"""
Concurrency tests: queue item accept race conditions.

10 tests verifying queue item acceptance idempotency and authorization.
"""
from __future__ import annotations

import uuid
import pytest
from fastapi.testclient import TestClient


def _create_and_assign_queue_item(client, started_contract, student_headers, admin_headers, approved_professor_headers):
    """Create a dispute, assign professor, return (dispute_id, queue_item_id)."""
    contract_id = started_contract["contract_id"]
    dispute_resp = client.post(
        "/api/v1/disputes",
        json={"contract_id": contract_id, "reason": "Queue race condition test dispute"},
        headers=student_headers,
    )
    assert dispute_resp.status_code in (200, 201), dispute_resp.text
    dispute_id = dispute_resp.json()["data"]["id"]

    prof_resp = client.get("/api/v1/professor/profile", headers=approved_professor_headers)
    profile_id = prof_resp.json()["id"]

    assign_resp = client.post(
        f"/api/v1/admin/disputes/{dispute_id}/assign-professor",
        json={"professor_id": profile_id},
        headers=admin_headers,
    )
    assert assign_resp.status_code == 200
    queue_item_id = assign_resp.json()["data"]["queue_item_id"]
    return dispute_id, queue_item_id


def _make_approved_professor(client, admin_headers, db):
    from app.models.user import User
    email = f"p-race-{uuid.uuid4().hex[:8]}@test.com"
    client.post("/api/v1/auth/register", json={
        "email": email, "password": "TestPassword123!",
        "first_name": "Race", "last_name": "Prof", "role": "student"
    })
    user = db.query(User).filter(User.email == email).first()
    user.role = "professor"
    db.commit()
    login = client.post("/api/v1/auth/login", json={"email": email, "password": "TestPassword123!"})
    token = login.json()["data"]["access_token"]
    prof_headers = {"Authorization": f"Bearer {token}"}
    prof_resp = client.post(
        "/api/v1/professor/profile",
        json={"bio": "Race test", "title": "Dr.", "department": "CS",
              "expertise_areas": [], "review_subjects": []},
        headers=prof_headers,
    )
    profile_id = prof_resp.json()["id"]
    client.post(
        f"/api/v1/admin/professors/{profile_id}/action",
        json={"action": "approve"},
        headers=admin_headers,
    )
    return prof_headers, profile_id


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_accept_queue_item_twice_returns_409(
    client: TestClient,
    started_contract: dict,
    student_headers: dict,
    admin_headers: dict,
    approved_professor_headers: dict,
) -> None:
    _, queue_item_id = _create_and_assign_queue_item(
        client, started_contract, student_headers, admin_headers, approved_professor_headers
    )

    r1 = client.post(
        f"/api/v1/professor/queue/{queue_item_id}/accept",
        headers=approved_professor_headers,
    )
    assert r1.status_code == 200

    r2 = client.post(
        f"/api/v1/professor/queue/{queue_item_id}/accept",
        headers=approved_professor_headers,
    )
    assert r2.status_code == 409


def test_accept_queue_item_assigned_to_another_professor_returns_403(
    client: TestClient,
    started_contract: dict,
    student_headers: dict,
    admin_headers: dict,
    approved_professor_headers: dict,
    db,
) -> None:
    _, queue_item_id = _create_and_assign_queue_item(
        client, started_contract, student_headers, admin_headers, approved_professor_headers
    )

    # Create another approved professor
    other_headers, _ = _make_approved_professor(client, admin_headers, db)

    resp = client.post(
        f"/api/v1/professor/queue/{queue_item_id}/accept",
        headers=other_headers,
    )
    assert resp.status_code == 403


def test_accept_nonexistent_queue_item_returns_404(
    client: TestClient, approved_professor_headers: dict
) -> None:
    fake_id = str(uuid.uuid4())
    resp = client.post(
        f"/api/v1/professor/queue/{fake_id}/accept",
        headers=approved_professor_headers,
    )
    assert resp.status_code == 404


def test_queue_item_status_in_progress_after_accept(
    client: TestClient,
    started_contract: dict,
    student_headers: dict,
    admin_headers: dict,
    approved_professor_headers: dict,
) -> None:
    _, queue_item_id = _create_and_assign_queue_item(
        client, started_contract, student_headers, admin_headers, approved_professor_headers
    )
    resp = client.post(
        f"/api/v1/professor/queue/{queue_item_id}/accept",
        headers=approved_professor_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_progress"


def test_student_cannot_accept_queue_item(
    client: TestClient,
    started_contract: dict,
    student_headers: dict,
    admin_headers: dict,
    approved_professor_headers: dict,
) -> None:
    _, queue_item_id = _create_and_assign_queue_item(
        client, started_contract, student_headers, admin_headers, approved_professor_headers
    )
    resp = client.post(
        f"/api/v1/professor/queue/{queue_item_id}/accept",
        headers=student_headers,
    )
    assert resp.status_code == 403


def test_researcher_cannot_accept_queue_item(
    client: TestClient,
    started_contract: dict,
    student_headers: dict,
    admin_headers: dict,
    approved_professor_headers: dict,
    researcher_headers: dict,
) -> None:
    _, queue_item_id = _create_and_assign_queue_item(
        client, started_contract, student_headers, admin_headers, approved_professor_headers
    )
    resp = client.post(
        f"/api/v1/professor/queue/{queue_item_id}/accept",
        headers=researcher_headers,
    )
    assert resp.status_code == 403


def test_after_accept_queue_shows_in_progress(
    client: TestClient,
    started_contract: dict,
    student_headers: dict,
    admin_headers: dict,
    approved_professor_headers: dict,
) -> None:
    _, queue_item_id = _create_and_assign_queue_item(
        client, started_contract, student_headers, admin_headers, approved_professor_headers
    )
    client.post(
        f"/api/v1/professor/queue/{queue_item_id}/accept",
        headers=approved_professor_headers,
    )
    queue_resp = client.get(
        "/api/v1/professor/queue?status_filter=in_progress",
        headers=approved_professor_headers,
    )
    assert queue_resp.status_code == 200
    items = queue_resp.json()
    item_ids = [i["id"] for i in items]
    assert queue_item_id in item_ids


def test_accept_completed_queue_item_returns_409(
    client: TestClient,
    started_contract: dict,
    student_headers: dict,
    admin_headers: dict,
    approved_professor_headers: dict,
    researcher_headers: dict,
) -> None:
    dispute_id, queue_item_id = _create_and_assign_queue_item(
        client, started_contract, student_headers, admin_headers, approved_professor_headers
    )
    # Accept
    client.post(
        f"/api/v1/professor/queue/{queue_item_id}/accept",
        headers=approved_professor_headers,
    )
    # Submit ruling (marks queue completed)
    client.post(
        f"/api/v1/professor/disputes/{dispute_id}/ruling",
        json={"ruling": "full_release",
              "reasoning": "Researcher completed the work to satisfaction per careful review of all deliverables. The quality meets the required standard and the contract terms have been fulfilled."},
        headers=approved_professor_headers,
    )
    # Try to accept again
    resp = client.post(
        f"/api/v1/professor/queue/{queue_item_id}/accept",
        headers=approved_professor_headers,
    )
    # Should fail — in_progress or completed
    assert resp.status_code == 409


def test_unauthenticated_cannot_accept_queue_item(
    client: TestClient,
    started_contract: dict,
    student_headers: dict,
    admin_headers: dict,
    approved_professor_headers: dict,
) -> None:
    _, queue_item_id = _create_and_assign_queue_item(
        client, started_contract, student_headers, admin_headers, approved_professor_headers
    )
    resp = client.post(f"/api/v1/professor/queue/{queue_item_id}/accept")
    assert resp.status_code == 401


def test_queue_item_assigned_not_assigned_to_other_professor(
    client: TestClient,
    started_contract: dict,
    student_headers: dict,
    admin_headers: dict,
    approved_professor_headers: dict,
    db,
) -> None:
    """Second professor's queue is empty (queue item assigned to first professor)."""
    _, queue_item_id = _create_and_assign_queue_item(
        client, started_contract, student_headers, admin_headers, approved_professor_headers
    )
    # Create second professor
    other_headers, _ = _make_approved_professor(client, admin_headers, db)
    # Second professor's queue should not show the item
    queue_resp = client.get("/api/v1/professor/queue", headers=other_headers)
    assert queue_resp.status_code == 200
    item_ids = [i["id"] for i in queue_resp.json()]
    assert queue_item_id not in item_ids
