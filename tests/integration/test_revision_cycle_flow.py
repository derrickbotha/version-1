"""
Integration tests: submit → revision request → resubmit → approve.

10 tests covering the full revision cycle.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def _get_submissions(client, headers, contract_id):
    resp = client.get(f"/api/v1/contracts/{contract_id}/submissions", headers=headers)
    assert resp.status_code == 200
    return resp.json()["data"]["items"]


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_researcher_submits_initial_work(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
) -> None:
    contract_id = started_contract["contract_id"]
    resp = client.post(
        "/api/v1/submissions",
        json={"contract_id": contract_id, "submission_notes": "Initial submission of work"},
        headers=researcher_headers,
    )
    assert resp.status_code in (200, 201)
    assert resp.json()["data"]["status"] == "submitted"


def test_student_requests_revision(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
) -> None:
    contract_id = started_contract["contract_id"]
    client.post(
        "/api/v1/submissions",
        json={"contract_id": contract_id, "submission_notes": "Initial work"},
        headers=researcher_headers,
    )
    submissions = _get_submissions(client, student_headers, contract_id)
    sub_id = submissions[0]["id"]

    resp = client.post(
        f"/api/v1/submissions/{sub_id}/revision",
        json={"message": "Please add more detail to the methodology section"},
        headers=student_headers,
    )
    assert resp.status_code in (200, 201)


def test_revision_request_changes_contract_status(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
) -> None:
    contract_id = started_contract["contract_id"]
    client.post(
        "/api/v1/submissions",
        json={"contract_id": contract_id, "submission_notes": "Initial work"},
        headers=researcher_headers,
    )
    submissions = _get_submissions(client, student_headers, contract_id)
    sub_id = submissions[0]["id"]
    client.post(
        f"/api/v1/submissions/{sub_id}/revision",
        json={"message": "Needs more references"},
        headers=student_headers,
    )
    contracts_resp = client.get("/api/v1/contracts", headers=student_headers)
    contracts = contracts_resp.json()["data"]["items"]
    contract = [c for c in contracts if c["id"] == contract_id][0]
    assert contract["status"] == "revision_requested"


def test_researcher_resubmits_after_revision(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
) -> None:
    contract_id = started_contract["contract_id"]
    # Submit
    client.post(
        "/api/v1/submissions",
        json={"contract_id": contract_id, "submission_notes": "Initial submission of completed work"},
        headers=researcher_headers,
    )
    # Request revision
    submissions = _get_submissions(client, student_headers, contract_id)
    client.post(
        f"/api/v1/submissions/{submissions[0]['id']}/revision",
        json={"message": "Please revise"},
        headers=student_headers,
    )
    # Resubmit
    resp = client.post(
        "/api/v1/submissions",
        json={"contract_id": contract_id, "submission_notes": "Revised work with all requested changes"},
        headers=researcher_headers,
    )
    assert resp.status_code in (200, 201)


def test_student_approves_second_submission(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
) -> None:
    contract_id = started_contract["contract_id"]
    # Submit
    client.post(
        "/api/v1/submissions",
        json={"contract_id": contract_id, "submission_notes": "Initial submission of completed work"},
        headers=researcher_headers,
    )
    subs = _get_submissions(client, student_headers, contract_id)
    # Revision
    client.post(
        f"/api/v1/submissions/{subs[0]['id']}/revision",
        json={"message": "Needs improvement"},
        headers=student_headers,
    )
    # Resubmit
    client.post(
        "/api/v1/submissions",
        json={"contract_id": contract_id, "submission_notes": "Revised submission addressing all feedback"},
        headers=researcher_headers,
    )
    # Get latest submission
    subs2 = _get_submissions(client, student_headers, contract_id)
    latest = max(subs2, key=lambda s: s["submitted_at"])

    resp = client.post(f"/api/v1/submissions/{latest['id']}/approve", headers=student_headers)
    assert resp.status_code == 200


def test_contract_completes_after_approval(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
) -> None:
    contract_id = started_contract["contract_id"]
    # Submit
    client.post(
        "/api/v1/submissions",
        json={"contract_id": contract_id, "submission_notes": "Completed all deliverables as specified"},
        headers=researcher_headers,
    )
    subs = _get_submissions(client, student_headers, contract_id)
    # Approve
    client.post(f"/api/v1/submissions/{subs[0]['id']}/approve", headers=student_headers)

    contracts_resp = client.get("/api/v1/contracts", headers=student_headers)
    contracts = contracts_resp.json()["data"]["items"]
    contract = [c for c in contracts if c["id"] == contract_id][0]
    assert contract["status"] == "completed"


def test_submission_status_submitted_after_submit(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
) -> None:
    contract_id = started_contract["contract_id"]
    resp = client.post(
        "/api/v1/submissions",
        json={"contract_id": contract_id, "submission_notes": "Work completed and ready for review"},
        headers=researcher_headers,
    )
    assert resp.json()["data"]["status"] == "submitted"


def test_only_student_can_request_revision(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
) -> None:
    contract_id = started_contract["contract_id"]
    client.post(
        "/api/v1/submissions",
        json={"contract_id": contract_id, "submission_notes": "Work completed and ready for review"},
        headers=researcher_headers,
    )
    # researcher trying to request revision on own submission - should fail
    submissions_resp = client.get(
        f"/api/v1/contracts/{contract_id}/submissions",
        headers=researcher_headers,
    )
    sub_id = submissions_resp.json()["data"]["items"][0]["id"]
    resp = client.post(
        f"/api/v1/submissions/{sub_id}/revision",
        json={"message": "Requesting revision on own work"},
        headers=researcher_headers,
    )
    assert resp.status_code == 403


def test_two_submissions_in_list_after_revision_cycle(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
) -> None:
    contract_id = started_contract["contract_id"]
    # Submit
    client.post(
        "/api/v1/submissions",
        json={"contract_id": contract_id, "submission_notes": "First submission of completed work"},
        headers=researcher_headers,
    )
    subs = _get_submissions(client, student_headers, contract_id)
    # Revision
    client.post(
        f"/api/v1/submissions/{subs[0]['id']}/revision",
        json={"message": "Please revise"},
        headers=student_headers,
    )
    # Resubmit
    client.post(
        "/api/v1/submissions",
        json={"contract_id": contract_id, "submission_notes": "Second revised submission with updates"},
        headers=researcher_headers,
    )
    subs2 = _get_submissions(client, student_headers, contract_id)
    assert len(subs2) == 2


def test_researcher_can_view_own_contract_submissions(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
) -> None:
    contract_id = started_contract["contract_id"]
    client.post(
        "/api/v1/submissions",
        json={"contract_id": contract_id, "submission_notes": "Work completed and ready for review"},
        headers=researcher_headers,
    )
    resp = client.get(
        f"/api/v1/contracts/{contract_id}/submissions",
        headers=researcher_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] >= 1
