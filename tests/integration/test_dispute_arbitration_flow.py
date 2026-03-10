"""
Integration tests: dispute arbitration full flow.

15 tests:
- Open dispute
- Admin assigns professor
- Professor accepts queue item
- Professor submits ruling
- Admin resolves dispute
- Dispute closes, payment settled
"""
from __future__ import annotations

import uuid
import pytest
from fastapi.testclient import TestClient


def _open_dispute(client, started_contract, student_headers) -> dict:
    contract_id = started_contract["contract_id"]
    resp = client.post(
        "/api/v1/disputes",
        json={"contract_id": contract_id, "reason": "Work quality is unacceptable and does not meet standards"},
        headers=student_headers,
    )
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["data"]


def _create_approved_professor_with_headers(client, admin_headers, db):
    """Returns (prof_headers, profile_id)."""
    from app.models.user import User
    email = f"arb-{uuid.uuid4().hex[:8]}@test.com"
    password = "TestPassword123!"
    client.post("/api/v1/auth/register", json={
        "email": email, "password": password,
        "first_name": "Arbitrator", "last_name": "Prof", "role": "student"
    })
    user = db.query(User).filter(User.email == email).first()
    user.role = "professor"
    db.commit()
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    token = login.json()["data"]["access_token"]
    prof_headers = {"Authorization": f"Bearer {token}"}
    prof_resp = client.post(
        "/api/v1/professor/profile",
        json={"bio": "Arbitration expert", "title": "Dr.", "department": "Law",
              "expertise_areas": ["Dispute Resolution"], "review_subjects": ["Mathematics"]},
        headers=prof_headers,
    )
    assert prof_resp.status_code in (200, 201), prof_resp.text
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

def test_open_dispute_on_in_progress_contract(
    client: TestClient,
    started_contract: dict,
    student_headers: dict,
) -> None:
    dispute = _open_dispute(client, started_contract, student_headers)
    assert dispute["id"] is not None
    assert dispute["status"] == "open"


def test_dispute_changes_contract_status_to_disputed(
    client: TestClient,
    started_contract: dict,
    student_headers: dict,
) -> None:
    contract_id = started_contract["contract_id"]
    _open_dispute(client, started_contract, student_headers)

    contracts_resp = client.get("/api/v1/contracts", headers=student_headers)
    contracts = contracts_resp.json()["data"]["items"]
    contract = [c for c in contracts if c["id"] == contract_id][0]
    assert contract["status"] == "disputed"


def test_admin_assigns_professor_to_dispute(
    client: TestClient,
    started_contract: dict,
    student_headers: dict,
    admin_headers: dict,
    db,
) -> None:
    dispute = _open_dispute(client, started_contract, student_headers)
    _, profile_id = _create_approved_professor_with_headers(client, admin_headers, db)

    resp = client.post(
        f"/api/v1/admin/disputes/{dispute['id']}/assign-professor",
        json={"professor_id": profile_id},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert "queue_item_id" in resp.json()["data"]


def test_assign_professor_sets_dispute_to_investigating(
    client: TestClient,
    started_contract: dict,
    student_headers: dict,
    admin_headers: dict,
    db,
) -> None:
    dispute = _open_dispute(client, started_contract, student_headers)
    _, profile_id = _create_approved_professor_with_headers(client, admin_headers, db)

    client.post(
        f"/api/v1/admin/disputes/{dispute['id']}/assign-professor",
        json={"professor_id": profile_id},
        headers=admin_headers,
    )
    # Check admin dispute list for status
    resp = client.get("/api/v1/admin/disputes", headers=admin_headers)
    items = resp.json()["data"]["items"]
    dispute_item = [d for d in items if d["id"] == dispute["id"]][0]
    assert dispute_item["status"] == "investigating"


def test_professor_accepts_queue_item(
    client: TestClient,
    started_contract: dict,
    student_headers: dict,
    admin_headers: dict,
    db,
) -> None:
    dispute = _open_dispute(client, started_contract, student_headers)
    prof_headers, profile_id = _create_approved_professor_with_headers(client, admin_headers, db)

    assign_resp = client.post(
        f"/api/v1/admin/disputes/{dispute['id']}/assign-professor",
        json={"professor_id": profile_id},
        headers=admin_headers,
    )
    queue_item_id = assign_resp.json()["data"]["queue_item_id"]

    accept_resp = client.post(
        f"/api/v1/professor/queue/{queue_item_id}/accept",
        headers=prof_headers,
    )
    assert accept_resp.status_code == 200
    assert accept_resp.json()["status"] == "in_progress"


def test_professor_submits_dispute_ruling(
    client: TestClient,
    started_contract: dict,
    student_headers: dict,
    admin_headers: dict,
    db,
) -> None:
    dispute = _open_dispute(client, started_contract, student_headers)
    prof_headers, profile_id = _create_approved_professor_with_headers(client, admin_headers, db)

    client.post(
        f"/api/v1/admin/disputes/{dispute['id']}/assign-professor",
        json={"professor_id": profile_id},
        headers=admin_headers,
    )

    ruling_resp = client.post(
        f"/api/v1/professor/disputes/{dispute['id']}/ruling",
        json={
            "ruling": "full_refund",
            "reasoning": "The researcher did not meet the agreed specifications outlined in the contract. The student is therefore entitled to a full refund of the escrowed amount.",
            "evidence_reviewed": "Job specification, submission text, messages",
        },
        headers=prof_headers,
    )
    assert ruling_resp.status_code in (200, 201), ruling_resp.text
    assert ruling_resp.json()["ruling"] == "full_refund"


def test_admin_resolves_dispute_after_professor_ruling(
    client: TestClient,
    started_contract: dict,
    student_headers: dict,
    admin_headers: dict,
    db,
) -> None:
    dispute = _open_dispute(client, started_contract, student_headers)
    prof_headers, profile_id = _create_approved_professor_with_headers(client, admin_headers, db)

    client.post(
        f"/api/v1/admin/disputes/{dispute['id']}/assign-professor",
        json={"professor_id": profile_id},
        headers=admin_headers,
    )
    client.post(
        f"/api/v1/professor/disputes/{dispute['id']}/ruling",
        json={
            "ruling": "full_refund",
            "reasoning": "Based on the evidence reviewed, the student's position is correct and the researcher failed to deliver as agreed. A full refund is warranted.",
        },
        headers=prof_headers,
    )

    resolve_resp = client.post(
        f"/api/v1/admin/disputes/{dispute['id']}/resolve",
        json={
            "resolution": "Admin confirms professor ruling. Student receives full refund of payment.",
            "financial_action": "full_refund",
        },
        headers=admin_headers,
    )
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["data"]["status"] == "resolved"


def test_dispute_closes_after_admin_resolution(
    client: TestClient,
    started_contract: dict,
    student_headers: dict,
    admin_headers: dict,
) -> None:
    dispute = _open_dispute(client, started_contract, student_headers)
    client.post(
        f"/api/v1/admin/disputes/{dispute['id']}/resolve",
        json={
            "resolution": "Admin resolves without professor. Student receives full refund.",
            "financial_action": "full_refund",
        },
        headers=admin_headers,
    )
    # Dispute is now resolved
    disputes_resp = client.get("/api/v1/admin/disputes", headers=admin_headers)
    items = disputes_resp.json()["data"]["items"]
    dispute_item = [d for d in items if d["id"] == dispute["id"]][0]
    assert dispute_item["status"] == "resolved"


def test_cannot_open_second_dispute_on_same_contract(
    client: TestClient,
    started_contract: dict,
    student_headers: dict,
) -> None:
    contract_id = started_contract["contract_id"]
    _open_dispute(client, started_contract, student_headers)
    # Try to open another dispute
    resp = client.post(
        "/api/v1/disputes",
        json={"contract_id": contract_id, "reason": "Second dispute on same contract should fail"},
        headers=student_headers,
    )
    assert resp.status_code == 400


def test_non_participant_cannot_open_dispute(
    client: TestClient,
    started_contract: dict,
    admin_headers: dict,
) -> None:
    """Admin is not a contract participant; cannot open dispute."""
    contract_id = started_contract["contract_id"]
    resp = client.post(
        "/api/v1/disputes",
        json={"contract_id": contract_id, "reason": "Admin opening dispute — should fail"},
        headers=admin_headers,
    )
    assert resp.status_code == 403


def test_dispute_payment_settled_after_release_resolution(
    client: TestClient,
    started_contract: dict,
    student_headers: dict,
    admin_headers: dict,
) -> None:
    dispute = _open_dispute(client, started_contract, student_headers)
    client.post(
        f"/api/v1/admin/disputes/{dispute['id']}/resolve",
        json={
            "resolution": "Researcher completed the work to acceptable standards as verified.",
            "financial_action": "full_release",
        },
        headers=admin_headers,
    )
    # Contract should be completed
    contracts_resp = client.get("/api/v1/contracts", headers=student_headers)
    contracts = contracts_resp.json()["data"]["items"]
    contract = [c for c in contracts if c["id"] == started_contract["contract_id"]][0]
    assert contract["status"] == "completed"


def test_user_can_view_own_disputes(
    client: TestClient,
    started_contract: dict,
    student_headers: dict,
) -> None:
    _open_dispute(client, started_contract, student_headers)
    resp = client.get("/api/v1/disputes/mine", headers=student_headers)
    assert resp.status_code == 200
    assert len(resp.json()["data"]["items"]) >= 1


def test_assigned_professor_sees_dispute_in_queue(
    client: TestClient,
    started_contract: dict,
    student_headers: dict,
    admin_headers: dict,
    db,
) -> None:
    dispute = _open_dispute(client, started_contract, student_headers)
    prof_headers, profile_id = _create_approved_professor_with_headers(client, admin_headers, db)

    client.post(
        f"/api/v1/admin/disputes/{dispute['id']}/assign-professor",
        json={"professor_id": profile_id},
        headers=admin_headers,
    )

    resp = client.get("/api/v1/professor/disputes", headers=prof_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_double_professor_assignment_to_same_dispute_fails(
    client: TestClient,
    started_contract: dict,
    student_headers: dict,
    admin_headers: dict,
    db,
) -> None:
    dispute = _open_dispute(client, started_contract, student_headers)
    _, profile_id = _create_approved_professor_with_headers(client, admin_headers, db)

    client.post(
        f"/api/v1/admin/disputes/{dispute['id']}/assign-professor",
        json={"professor_id": profile_id},
        headers=admin_headers,
    )
    # Second assignment to same dispute should fail
    resp = client.post(
        f"/api/v1/admin/disputes/{dispute['id']}/assign-professor",
        json={"professor_id": profile_id},
        headers=admin_headers,
    )
    assert resp.status_code == 409
