"""
Tests for the submissions API endpoints.

POST /api/v1/submissions
GET  /api/v1/contracts/{id}/submissions
GET  /api/v1/submissions/{id}
POST /api/v1/submissions/{id}/approve
POST /api/v1/submissions/{id}/revision
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient


SUBMISSION_NOTES = "Here is my completed research. I have covered all required topics."


def _submit_work(client, contract_id, researcher_headers):
    resp = client.post("/api/v1/submissions",
                       json={"contract_id": contract_id, "submission_notes": SUBMISSION_NOTES},
                       headers=researcher_headers)
    assert resp.status_code in (200, 201), f"Submit failed: {resp.text}"
    return resp.json()["data"]


# ---------------------------------------------------------------------------
# Create submission
# ---------------------------------------------------------------------------

def test_researcher_can_submit_work(client, researcher_headers, started_contract):
    """Researcher can submit work on an in_progress contract."""
    resp = client.post("/api/v1/submissions",
                       json={"contract_id": started_contract["contract_id"],
                             "submission_notes": SUBMISSION_NOTES},
                       headers=researcher_headers)
    assert resp.status_code in (200, 201)


def test_submission_returns_correct_data(client, researcher_headers, started_contract):
    """Submission response contains expected fields."""
    sub = _submit_work(client, started_contract["contract_id"], researcher_headers)
    assert "id" in sub
    assert sub["contract_id"] == started_contract["contract_id"]
    assert sub["status"] == "submitted"
    assert sub["submission_notes"] == SUBMISSION_NOTES


def test_submission_on_non_in_progress_contract_returns_400(client, student_headers,
                                                              researcher_headers, full_contract):
    """Submitting work on a non-in_progress contract (accepted status) returns 400."""
    resp = client.post("/api/v1/submissions",
                       json={"contract_id": full_contract["contract_id"],
                             "submission_notes": SUBMISSION_NOTES},
                       headers=researcher_headers)
    assert resp.status_code == 400


def test_student_cannot_submit_work(client, student_headers, started_contract):
    """Student cannot create a submission (researcher only)."""
    resp = client.post("/api/v1/submissions",
                       json={"contract_id": started_contract["contract_id"],
                             "submission_notes": SUBMISSION_NOTES},
                       headers=student_headers)
    assert resp.status_code == 403


def test_wrong_researcher_cannot_submit(client, started_contract, db):
    """A different researcher cannot submit for a contract they don't own."""
    from tests.conftest import auth_headers
    other_researcher_headers = auth_headers(client, "researcher")
    resp = client.post("/api/v1/submissions",
                       json={"contract_id": started_contract["contract_id"],
                             "submission_notes": SUBMISSION_NOTES},
                       headers=other_researcher_headers)
    assert resp.status_code == 403


def test_unauthenticated_cannot_submit(client, started_contract):
    """Unauthenticated request returns 401."""
    resp = client.post("/api/v1/submissions",
                       json={"contract_id": started_contract["contract_id"],
                             "submission_notes": SUBMISSION_NOTES})
    assert resp.status_code == 401


def test_submission_on_nonexistent_contract_returns_404(client, researcher_headers):
    """Submitting for a non-existent contract returns 404."""
    resp = client.post("/api/v1/submissions",
                       json={"contract_id": str(uuid.uuid4()),
                             "submission_notes": SUBMISSION_NOTES},
                       headers=researcher_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# List submissions for a contract
# ---------------------------------------------------------------------------

def test_student_can_view_submissions(client, student_headers, researcher_headers, started_contract):
    """Student can view submissions for their contract."""
    _submit_work(client, started_contract["contract_id"], researcher_headers)
    resp = client.get(f"/api/v1/contracts/{started_contract['contract_id']}/submissions",
                      headers=student_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] >= 1


def test_researcher_can_view_submissions(client, researcher_headers, started_contract):
    """Researcher can view submissions for their contract."""
    _submit_work(client, started_contract["contract_id"], researcher_headers)
    resp = client.get(f"/api/v1/contracts/{started_contract['contract_id']}/submissions",
                      headers=researcher_headers)
    assert resp.status_code == 200


def test_non_participant_cannot_view_submissions(client, started_contract, db):
    """Non-participant cannot view submissions."""
    from tests.conftest import auth_headers
    other_headers = auth_headers(client, "student")
    resp = client.get(f"/api/v1/contracts/{started_contract['contract_id']}/submissions",
                      headers=other_headers)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Approve submission
# ---------------------------------------------------------------------------

def test_student_can_approve_submission(client, student_headers, researcher_headers, started_contract):
    """Student can approve a submitted work."""
    sub = _submit_work(client, started_contract["contract_id"], researcher_headers)
    resp = client.post(f"/api/v1/submissions/{sub['id']}/approve", headers=student_headers)
    assert resp.status_code == 200


def test_approved_submission_has_approved_status(client, student_headers, researcher_headers,
                                                   started_contract):
    """Approving a submission sets its status to approved."""
    sub = _submit_work(client, started_contract["contract_id"], researcher_headers)
    resp = client.post(f"/api/v1/submissions/{sub['id']}/approve", headers=student_headers)
    data = resp.json()["data"]
    assert data["status"] == "approved"


def test_approve_submission_changes_contract_to_completed(client, student_headers,
                                                            researcher_headers, started_contract):
    """Approving a submission transitions the contract to completed."""
    sub = _submit_work(client, started_contract["contract_id"], researcher_headers)
    client.post(f"/api/v1/submissions/{sub['id']}/approve", headers=student_headers)
    # Verify contract status
    resp = client.get(f"/api/v1/contracts/{started_contract['contract_id']}",
                      headers=student_headers)
    assert resp.json()["data"]["status"] == "completed"


def test_researcher_cannot_approve_submission(client, researcher_headers, started_contract):
    """Researcher cannot approve a submission (student only)."""
    sub = _submit_work(client, started_contract["contract_id"], researcher_headers)
    resp = client.post(f"/api/v1/submissions/{sub['id']}/approve", headers=researcher_headers)
    assert resp.status_code == 403


def test_cannot_approve_already_approved_submission(client, student_headers, researcher_headers,
                                                     started_contract):
    """Cannot approve a submission that is already approved."""
    sub = _submit_work(client, started_contract["contract_id"], researcher_headers)
    client.post(f"/api/v1/submissions/{sub['id']}/approve", headers=student_headers)
    resp = client.post(f"/api/v1/submissions/{sub['id']}/approve", headers=student_headers)
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Request revision
# ---------------------------------------------------------------------------

def test_student_can_request_revision(client, student_headers, researcher_headers, started_contract):
    """Student can request a revision on a submitted work."""
    sub = _submit_work(client, started_contract["contract_id"], researcher_headers)
    resp = client.post(f"/api/v1/submissions/{sub['id']}/revision",
                       json={"message": "Please revise section 2 and add more references."},
                       headers=student_headers)
    assert resp.status_code in (200, 201)


def test_revision_changes_contract_to_revision_requested(client, student_headers,
                                                          researcher_headers, started_contract):
    """Requesting revision transitions contract to revision_requested."""
    sub = _submit_work(client, started_contract["contract_id"], researcher_headers)
    client.post(f"/api/v1/submissions/{sub['id']}/revision",
                json={"message": "Please revise section 2 and add more references."},
                headers=student_headers)
    resp = client.get(f"/api/v1/contracts/{started_contract['contract_id']}",
                      headers=student_headers)
    assert resp.json()["data"]["status"] == "revision_requested"


def test_researcher_can_resubmit_after_revision(client, student_headers, researcher_headers,
                                                  started_contract):
    """Researcher can resubmit work after a revision request."""
    sub = _submit_work(client, started_contract["contract_id"], researcher_headers)
    client.post(f"/api/v1/submissions/{sub['id']}/revision",
                json={"message": "Please revise section 2 and add more references."},
                headers=student_headers)
    # Now resubmit
    resp = client.post("/api/v1/submissions",
                       json={"contract_id": started_contract["contract_id"],
                             "submission_notes": "Revised version with all requested changes."},
                       headers=researcher_headers)
    assert resp.status_code in (200, 201)


def test_researcher_cannot_request_revision(client, researcher_headers, started_contract):
    """Researcher cannot request a revision (student only)."""
    sub = _submit_work(client, started_contract["contract_id"], researcher_headers)
    resp = client.post(f"/api/v1/submissions/{sub['id']}/revision",
                       json={"message": "Need changes."},
                       headers=researcher_headers)
    assert resp.status_code == 403


def test_cannot_revise_approved_submission(client, student_headers, researcher_headers,
                                            started_contract):
    """Cannot request revision on an already approved submission."""
    sub = _submit_work(client, started_contract["contract_id"], researcher_headers)
    client.post(f"/api/v1/submissions/{sub['id']}/approve", headers=student_headers)
    resp = client.post(f"/api/v1/submissions/{sub['id']}/revision",
                       json={"message": "Wait, I want changes after all."},
                       headers=student_headers)
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Get submission by ID
# ---------------------------------------------------------------------------

def test_get_submission_by_id(client, student_headers, researcher_headers, started_contract):
    """Can get a submission by ID."""
    sub = _submit_work(client, started_contract["contract_id"], researcher_headers)
    resp = client.get(f"/api/v1/submissions/{sub['id']}", headers=student_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == sub["id"]


def test_get_nonexistent_submission_returns_404(client, student_headers):
    """GET /submissions/{nonexistent_id} returns 404."""
    resp = client.get(f"/api/v1/submissions/{uuid.uuid4()}", headers=student_headers)
    assert resp.status_code == 404
