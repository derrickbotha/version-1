"""
Tests for professor quality review endpoints.

POST /api/v1/professor/reviews/contract/{id}
GET  /api/v1/professor/reviews
GET  /api/v1/professor/reviews/contract/{id}
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient


REVIEW_PAYLOAD_APPROVED = {
    "score": 85,
    "originality_score": 90,
    "feedback": ("This is an excellent piece of research that demonstrates thorough "
                 "understanding of the topic. The methodology is sound and the conclusions "
                 "are well-supported by evidence."),
    "verdict": "approved",
}

REVIEW_PAYLOAD_REVISION = {
    "score": 55,
    "originality_score": 75,
    "feedback": ("The research shows promise but needs significant improvement in the "
                 "literature review section. The methodology section lacks sufficient detail "
                 "and the conclusions need to be better supported by the data presented."),
    "verdict": "revision_required",
}

REVIEW_PAYLOAD_REJECTED = {
    "score": 20,
    "originality_score": 10,
    "feedback": ("This submission shows significant plagiarism and does not meet the minimum "
                 "academic standards required. The work fails to demonstrate original thought "
                 "and the references are improperly cited throughout the document."),
    "verdict": "rejected",
}


def _submit_work_for_review(client, started_contract, researcher_headers):
    """Submit work on a started contract."""
    resp = client.post("/api/v1/submissions",
                       json={"contract_id": started_contract["contract_id"],
                             "submission_notes": "Work submitted for professor review."},
                       headers=researcher_headers)
    assert resp.status_code in (200, 201)
    return resp.json()["data"]


def _submit_review(client, contract_id, approved_professor_headers, payload=None):
    payload = payload or REVIEW_PAYLOAD_APPROVED
    resp = client.post(f"/api/v1/professor/reviews/contract/{contract_id}",
                       json=payload,
                       headers=approved_professor_headers)
    assert resp.status_code in (200, 201), f"Submit review failed: {resp.text}"
    return resp.json()


# ---------------------------------------------------------------------------
# Submit review
# ---------------------------------------------------------------------------

def test_approved_professor_can_submit_review_approved(
    client, approved_professor_headers, researcher_headers, started_contract
):
    """Approved professor can submit a review with verdict=approved."""
    _submit_work_for_review(client, started_contract, researcher_headers)
    resp = client.post(
        f"/api/v1/professor/reviews/contract/{started_contract['contract_id']}",
        json=REVIEW_PAYLOAD_APPROVED,
        headers=approved_professor_headers,
    )
    assert resp.status_code in (200, 201)


def test_review_response_contains_required_fields(
    client, approved_professor_headers, researcher_headers, started_contract
):
    """Review response contains expected fields."""
    _submit_work_for_review(client, started_contract, researcher_headers)
    review = _submit_review(client, started_contract["contract_id"],
                            approved_professor_headers, REVIEW_PAYLOAD_APPROVED)
    assert "id" in review
    assert review["contract_id"] == started_contract["contract_id"]
    assert review["score"] == REVIEW_PAYLOAD_APPROVED["score"]
    assert review["status"] == "approved"


def test_approved_verdict_sets_contract_to_completed(
    client, student_headers, approved_professor_headers, researcher_headers, started_contract
):
    """Approved verdict transitions contract to completed."""
    _submit_work_for_review(client, started_contract, researcher_headers)
    _submit_review(client, started_contract["contract_id"],
                   approved_professor_headers, REVIEW_PAYLOAD_APPROVED)
    resp = client.get(f"/api/v1/contracts/{started_contract['contract_id']}",
                      headers=student_headers)
    assert resp.json()["data"]["status"] == "completed"


def test_revision_required_verdict_sets_contract_to_revision_requested(
    client, student_headers, approved_professor_headers, researcher_headers, started_contract
):
    """revision_required verdict transitions contract to revision_requested."""
    _submit_work_for_review(client, started_contract, researcher_headers)
    _submit_review(client, started_contract["contract_id"],
                   approved_professor_headers, REVIEW_PAYLOAD_REVISION)
    resp = client.get(f"/api/v1/contracts/{started_contract['contract_id']}",
                      headers=student_headers)
    assert resp.json()["data"]["status"] == "revision_requested"


def test_rejected_verdict_sets_contract_to_disputed(
    client, student_headers, approved_professor_headers, researcher_headers, started_contract
):
    """rejected verdict transitions contract to disputed."""
    _submit_work_for_review(client, started_contract, researcher_headers)
    _submit_review(client, started_contract["contract_id"],
                   approved_professor_headers, REVIEW_PAYLOAD_REJECTED)
    resp = client.get(f"/api/v1/contracts/{started_contract['contract_id']}",
                      headers=student_headers)
    assert resp.json()["data"]["status"] == "disputed"


def test_invalid_verdict_returns_422(
    client, approved_professor_headers, researcher_headers, started_contract
):
    """Invalid verdict returns 422."""
    _submit_work_for_review(client, started_contract, researcher_headers)
    resp = client.post(
        f"/api/v1/professor/reviews/contract/{started_contract['contract_id']}",
        json={**REVIEW_PAYLOAD_APPROVED, "verdict": "maybe"},
        headers=approved_professor_headers,
    )
    assert resp.status_code in (422, 409)


def test_pending_professor_cannot_review(
    client, professor_headers, researcher_headers, started_contract
):
    """Professor with pending profile cannot submit review (403)."""
    client.post("/api/v1/professor/profile",
                json={"bio": "Pending", "title": "Dr.", "department": "CS",
                      "expertise_areas": [], "review_subjects": []},
                headers=professor_headers)
    _submit_work_for_review(client, started_contract, researcher_headers)
    resp = client.post(
        f"/api/v1/professor/reviews/contract/{started_contract['contract_id']}",
        json=REVIEW_PAYLOAD_APPROVED,
        headers=professor_headers,
    )
    assert resp.status_code == 403


def test_student_cannot_submit_review(
    client, student_headers, researcher_headers, started_contract
):
    """Student cannot submit a review (403)."""
    _submit_work_for_review(client, started_contract, researcher_headers)
    resp = client.post(
        f"/api/v1/professor/reviews/contract/{started_contract['contract_id']}",
        json=REVIEW_PAYLOAD_APPROVED,
        headers=student_headers,
    )
    assert resp.status_code == 403


def test_feedback_too_short_returns_422(
    client, approved_professor_headers, researcher_headers, started_contract
):
    """Feedback must be at least 50 chars."""
    _submit_work_for_review(client, started_contract, researcher_headers)
    resp = client.post(
        f"/api/v1/professor/reviews/contract/{started_contract['contract_id']}",
        json={**REVIEW_PAYLOAD_APPROVED, "feedback": "Too short."},
        headers=approved_professor_headers,
    )
    assert resp.status_code == 422


def test_review_requires_auth(client, started_contract):
    """Submitting a review requires authentication."""
    resp = client.post(
        f"/api/v1/professor/reviews/contract/{started_contract['contract_id']}",
        json=REVIEW_PAYLOAD_APPROVED,
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Get reviews by professor
# ---------------------------------------------------------------------------

def test_get_reviews_by_professor(
    client, approved_professor_headers, researcher_headers, started_contract
):
    """Professor can list their own reviews."""
    _submit_work_for_review(client, started_contract, researcher_headers)
    _submit_review(client, started_contract["contract_id"], approved_professor_headers)
    resp = client.get("/api/v1/professor/reviews", headers=approved_professor_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_get_reviews_returns_empty_when_none(client, approved_professor_headers):
    """Returns empty list when professor has no reviews."""
    resp = client.get("/api/v1/professor/reviews", headers=approved_professor_headers)
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# Get reviews for contract
# ---------------------------------------------------------------------------

def test_get_contract_reviews(
    client, approved_professor_headers, researcher_headers, started_contract
):
    """Can get all reviews for a specific contract."""
    _submit_work_for_review(client, started_contract, researcher_headers)
    _submit_review(client, started_contract["contract_id"], approved_professor_headers)
    resp = client.get(
        f"/api/v1/professor/reviews/contract/{started_contract['contract_id']}",
        headers=approved_professor_headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_get_contract_reviews_returns_empty_when_none(
    client, approved_professor_headers, started_contract
):
    """Returns empty list when no reviews exist for the contract."""
    resp = client.get(
        f"/api/v1/professor/reviews/contract/{started_contract['contract_id']}",
        headers=approved_professor_headers,
    )
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_contract_reviews_requires_auth(client, started_contract):
    """GET /reviews/contract/{id} requires authentication."""
    resp = client.get(f"/api/v1/professor/reviews/contract/{started_contract['contract_id']}")
    assert resp.status_code == 401
