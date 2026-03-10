"""
Tests for professor analytics endpoint.

GET /api/v1/professor/analytics
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


REVIEW_FEEDBACK = (
    "This is an excellent piece of research that demonstrates thorough "
    "understanding of the topic. The methodology is sound and well documented. "
    "The conclusions are well-supported by evidence and references."
)


def _get_analytics(client, headers):
    resp = client.get("/api/v1/professor/analytics", headers=headers)
    assert resp.status_code == 200
    return resp.json()


# ---------------------------------------------------------------------------
# Analytics structure
# ---------------------------------------------------------------------------

def test_get_analytics_returns_200(client, approved_professor_headers):
    """GET /professor/analytics returns 200."""
    resp = client.get("/api/v1/professor/analytics", headers=approved_professor_headers)
    assert resp.status_code == 200


def test_get_analytics_returns_correct_structure(client, approved_professor_headers):
    """Analytics response contains all required fields."""
    analytics = _get_analytics(client, approved_professor_headers)
    required_fields = [
        "total_reviews",
        "pending_reviews",
        "completed_reviews",
        "avg_score_given",
        "total_fees_earned",
        "disputes_arbitrated",
        "credentials_verified",
        "endorsements_given",
        "sla_compliance_rate",
    ]
    for field in required_fields:
        assert field in analytics, f"Missing field: {field}"


def test_analytics_initial_values_are_zero(client, approved_professor_headers):
    """Fresh professor has zero stats."""
    analytics = _get_analytics(client, approved_professor_headers)
    assert analytics["total_reviews"] == 0
    assert analytics["completed_reviews"] == 0
    assert analytics["disputes_arbitrated"] == 0
    assert analytics["credentials_verified"] == 0
    assert analytics["endorsements_given"] == 0


def test_analytics_requires_professor_role(client, student_headers):
    """Analytics endpoint requires professor role."""
    resp = client.get("/api/v1/professor/analytics", headers=student_headers)
    assert resp.status_code == 403


def test_analytics_requires_auth(client):
    """Analytics endpoint requires authentication."""
    resp = client.get("/api/v1/professor/analytics")
    assert resp.status_code == 401


def test_pending_professor_can_view_analytics(client, professor_headers):
    """Even pending professor can view their analytics (profile must exist)."""
    client.post("/api/v1/professor/profile",
                json={"bio": "Test", "title": "Dr.", "department": "CS",
                      "expertise_areas": [], "review_subjects": []},
                headers=professor_headers)
    resp = client.get("/api/v1/professor/analytics", headers=professor_headers)
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Analytics accuracy after review
# ---------------------------------------------------------------------------

def test_total_reviews_increases_after_review(
    client, approved_professor_headers, researcher_headers, started_contract
):
    """total_reviews count increases after submitting a review."""
    before = _get_analytics(client, approved_professor_headers)["total_reviews"]

    # Submit work and review it
    client.post("/api/v1/submissions",
                json={"contract_id": started_contract["contract_id"],
                      "submission_notes": "Completed work."},
                headers=researcher_headers)
    client.post(f"/api/v1/professor/reviews/contract/{started_contract['contract_id']}",
                json={
                    "score": 80,
                    "originality_score": 85,
                    "feedback": REVIEW_FEEDBACK,
                    "verdict": "approved",
                },
                headers=approved_professor_headers)

    after = _get_analytics(client, approved_professor_headers)["total_reviews"]
    assert after == before + 1


def test_completed_reviews_increases_after_review(
    client, approved_professor_headers, researcher_headers, started_contract
):
    """completed_reviews increases after a review with a terminal verdict."""
    before = _get_analytics(client, approved_professor_headers)["completed_reviews"]

    client.post("/api/v1/submissions",
                json={"contract_id": started_contract["contract_id"],
                      "submission_notes": "Completed work."},
                headers=researcher_headers)
    client.post(f"/api/v1/professor/reviews/contract/{started_contract['contract_id']}",
                json={
                    "score": 80,
                    "originality_score": 85,
                    "feedback": REVIEW_FEEDBACK,
                    "verdict": "approved",
                },
                headers=approved_professor_headers)

    after = _get_analytics(client, approved_professor_headers)["completed_reviews"]
    assert after == before + 1


def test_sla_compliance_rate_in_response(client, approved_professor_headers):
    """sla_compliance_rate is a numeric value in response."""
    analytics = _get_analytics(client, approved_professor_headers)
    assert isinstance(analytics["sla_compliance_rate"], (int, float))


def test_fees_earned_in_response(client, approved_professor_headers):
    """total_fees_earned is present and numeric."""
    analytics = _get_analytics(client, approved_professor_headers)
    assert isinstance(analytics["total_fees_earned"], (int, float))


def test_endorsements_given_increases_after_endorsement(
    client, approved_professor_headers, researcher_headers
):
    """endorsements_given increases after creating an endorsement."""
    before = _get_analytics(client, approved_professor_headers)["endorsements_given"]

    researcher_id = client.get("/api/v1/auth/me", headers=researcher_headers).json()["data"]["id"]
    client.post("/api/v1/professor/endorsements",
                json={"researcher_id": researcher_id, "subject_area": "ML",
                      "endorsement_text": "Great researcher."},
                headers=approved_professor_headers)

    after = _get_analytics(client, approved_professor_headers)["endorsements_given"]
    assert after == before + 1


def test_credentials_verified_increases_after_verification(
    client, approved_professor_headers, researcher_headers
):
    """credentials_verified increases after verifying a credential."""
    before = _get_analytics(client, approved_professor_headers)["credentials_verified"]

    cred_resp = client.post("/api/v1/professor/credentials",
                            json={
                                "credential_type": "phd",
                                "institution_name": "Stanford University",
                                "field_of_study": "Computer Science",
                                "year_obtained": 2018,
                            },
                            headers=researcher_headers)
    cred_id = cred_resp.json()["id"]
    client.post(f"/api/v1/professor/credentials/{cred_id}/action",
                json={"action": "verify"},
                headers=approved_professor_headers)

    after = _get_analytics(client, approved_professor_headers)["credentials_verified"]
    assert after == before + 1
