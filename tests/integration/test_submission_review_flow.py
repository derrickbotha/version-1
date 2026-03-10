"""
Integration tests: contract in_progress → researcher submits → professor reviews.

20 tests covering:
- Submit work → contract becomes "submitted"
- Professor review approved → contract becomes "completed"
- Professor review revision_required → contract becomes "revision_requested"
- Researcher can resubmit after revision
- Professor review rejected → contract becomes "disputed"
- Review stats updated on professor profile
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def _submit_work(client, researcher_headers, contract_id, notes="Work completed"):
    resp = client.post(
        "/api/v1/submissions",
        json={"contract_id": contract_id, "submission_notes": notes},
        headers=researcher_headers,
    )
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["data"]


def _get_submissions(client, headers, contract_id):
    resp = client.get(f"/api/v1/contracts/{contract_id}/submissions", headers=headers)
    assert resp.status_code == 200
    return resp.json()["data"]["items"]


# ─────────────────────────────────────────────────────────────────────────────
# Submission tests
# ─────────────────────────────────────────────────────────────────────────────

def test_submit_work_creates_submission(
    client: TestClient, started_contract: dict, researcher_headers: dict
) -> None:
    contract_id = started_contract["contract_id"]
    submission = _submit_work(client, researcher_headers, contract_id)
    assert submission["id"] is not None
    assert submission["contract_id"] == contract_id


def test_submit_work_changes_contract_to_submitted(
    client: TestClient, started_contract: dict, researcher_headers: dict, student_headers: dict
) -> None:
    contract_id = started_contract["contract_id"]
    _submit_work(client, researcher_headers, contract_id)

    contracts_resp = client.get("/api/v1/contracts", headers=student_headers)
    contracts = contracts_resp.json()["data"]["items"]
    contract = [c for c in contracts if c["id"] == contract_id][0]
    assert contract["status"] == "submitted"


def test_professor_review_approved_completes_contract(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    approved_professor_headers: dict,
    student_headers: dict,
) -> None:
    contract_id = started_contract["contract_id"]
    _submit_work(client, researcher_headers, contract_id)

    review_resp = client.post(
        f"/api/v1/professor/reviews/contract/{contract_id}",
        json={
            "verdict": "approved",
            "score": 85,
            "feedback": "Excellent work meeting all requirements. The deliverables were thorough.",
        },
        headers=approved_professor_headers,
    )
    assert review_resp.status_code in (200, 201), review_resp.text

    # Contract should now be completed
    contracts_resp = client.get("/api/v1/contracts", headers=student_headers)
    contracts = contracts_resp.json()["data"]["items"]
    contract = [c for c in contracts if c["id"] == contract_id][0]
    assert contract["status"] == "completed"


def test_professor_review_revision_required_sets_revision_requested(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    approved_professor_headers: dict,
    student_headers: dict,
) -> None:
    contract_id = started_contract["contract_id"]
    _submit_work(client, researcher_headers, contract_id)

    review_resp = client.post(
        f"/api/v1/professor/reviews/contract/{contract_id}",
        json={
            "verdict": "revision_required",
            "score": 55,
            "feedback": "Work needs improvement in methodology section and must be revised.",
        },
        headers=approved_professor_headers,
    )
    assert review_resp.status_code in (200, 201), review_resp.text

    contracts_resp = client.get("/api/v1/contracts", headers=student_headers)
    contracts = contracts_resp.json()["data"]["items"]
    contract = [c for c in contracts if c["id"] == contract_id][0]
    assert contract["status"] == "revision_requested"


def test_researcher_can_resubmit_after_revision(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    approved_professor_headers: dict,
    student_headers: dict,
) -> None:
    contract_id = started_contract["contract_id"]
    _submit_work(client, researcher_headers, contract_id)

    # Professor requests revision
    client.post(
        f"/api/v1/professor/reviews/contract/{contract_id}",
        json={"verdict": "revision_required", "score": 55, "feedback": "Needs more detail. Please expand the analysis with additional supporting evidence."},
        headers=approved_professor_headers,
    )

    # Researcher resubmits
    resp = client.post(
        "/api/v1/submissions",
        json={"contract_id": contract_id, "submission_notes": "Revised work with improvements"},
        headers=researcher_headers,
    )
    assert resp.status_code in (200, 201), resp.text
    assert resp.json()["data"]["status"] == "submitted"


def test_professor_review_rejected_moves_contract_to_disputed(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    approved_professor_headers: dict,
    student_headers: dict,
) -> None:
    contract_id = started_contract["contract_id"]
    _submit_work(client, researcher_headers, contract_id)

    review_resp = client.post(
        f"/api/v1/professor/reviews/contract/{contract_id}",
        json={
            "verdict": "rejected",
            "score": 20,
            "feedback": "Work is plagiarized and does not meet academic standards.",
        },
        headers=approved_professor_headers,
    )
    assert review_resp.status_code in (200, 201), review_resp.text

    contracts_resp = client.get("/api/v1/contracts", headers=student_headers)
    contracts = contracts_resp.json()["data"]["items"]
    contract = [c for c in contracts if c["id"] == contract_id][0]
    assert contract["status"] == "disputed"


def test_review_stats_updated_on_professor_profile(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    approved_professor_headers: dict,
) -> None:
    contract_id = started_contract["contract_id"]
    _submit_work(client, researcher_headers, contract_id)

    client.post(
        f"/api/v1/professor/reviews/contract/{contract_id}",
        json={"verdict": "approved", "score": 90, "feedback": "Excellent work. The researcher demonstrated a thorough understanding of the topic."},
        headers=approved_professor_headers,
    )

    # Check analytics
    analytics_resp = client.get("/api/v1/professor/analytics", headers=approved_professor_headers)
    assert analytics_resp.status_code == 200
    data = analytics_resp.json()
    assert data["total_reviews"] >= 1
    assert data["completed_reviews"] >= 1


def test_review_round_number_increments(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    approved_professor_headers: dict,
) -> None:
    contract_id = started_contract["contract_id"]
    _submit_work(client, researcher_headers, contract_id)

    # First review
    r1 = client.post(
        f"/api/v1/professor/reviews/contract/{contract_id}",
        json={"verdict": "revision_required", "score": 55, "feedback": "Needs work. The methodology section requires significant improvement before approval."},
        headers=approved_professor_headers,
    )
    assert r1.json()["round_number"] == 1

    # Researcher resubmits
    client.post(
        "/api/v1/submissions",
        json={"contract_id": contract_id, "submission_notes": "Revised submission with improvements"},
        headers=researcher_headers,
    )

    # Second review
    r2 = client.post(
        f"/api/v1/professor/reviews/contract/{contract_id}",
        json={"verdict": "approved", "score": 80, "feedback": "Improved. The revisions address all the previously raised concerns satisfactorily."},
        headers=approved_professor_headers,
    )
    assert r2.json()["round_number"] == 2


def test_professor_can_list_own_reviews(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    approved_professor_headers: dict,
) -> None:
    contract_id = started_contract["contract_id"]
    _submit_work(client, researcher_headers, contract_id)
    client.post(
        f"/api/v1/professor/reviews/contract/{contract_id}",
        json={"verdict": "approved", "score": 80, "feedback": "Good work overall. The submission met all the required criteria and expectations."},
        headers=approved_professor_headers,
    )
    reviews_resp = client.get("/api/v1/professor/reviews", headers=approved_professor_headers)
    assert reviews_resp.status_code == 200
    assert len(reviews_resp.json()) >= 1


def test_contract_reviews_visible_to_all_parties(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    approved_professor_headers: dict,
    student_headers: dict,
) -> None:
    contract_id = started_contract["contract_id"]
    _submit_work(client, researcher_headers, contract_id)
    client.post(
        f"/api/v1/professor/reviews/contract/{contract_id}",
        json={"verdict": "approved", "score": 80, "feedback": "Good work overall. The submission met all the required criteria and expectations."},
        headers=approved_professor_headers,
    )
    # Student can see reviews
    reviews_resp = client.get(
        f"/api/v1/professor/reviews/contract/{contract_id}",
        headers=student_headers,
    )
    assert reviews_resp.status_code == 200
    assert len(reviews_resp.json()) >= 1


def test_cannot_submit_to_non_in_progress_contract(
    client: TestClient, full_contract: dict, researcher_headers: dict
) -> None:
    """full_contract is escrowed (not in_progress), so submission should fail."""
    contract_id = full_contract["contract_id"]
    resp = client.post(
        "/api/v1/submissions",
        json={"contract_id": contract_id, "submission_notes": "Work completed and ready for review"},
        headers=researcher_headers,
    )
    assert resp.status_code == 400


def test_student_cannot_submit_work(
    client: TestClient, started_contract: dict, student_headers: dict
) -> None:
    contract_id = started_contract["contract_id"]
    resp = client.post(
        "/api/v1/submissions",
        json={"contract_id": contract_id, "submission_notes": "Student submitting — should fail"},
        headers=student_headers,
    )
    assert resp.status_code == 403


def test_unapproved_professor_cannot_review(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    professor_headers: dict,
) -> None:
    """Professor without an approved profile cannot submit reviews."""
    contract_id = started_contract["contract_id"]
    _submit_work(client, researcher_headers, contract_id)
    resp = client.post(
        f"/api/v1/professor/reviews/contract/{contract_id}",
        json={"verdict": "approved", "score": 80, "feedback": "Good work overall. The submission met all the required criteria and expectations."},
        headers=professor_headers,
    )
    assert resp.status_code in (403, 404)  # 404 if no profile, 403 if profile not approved


def test_invalid_review_verdict_returns_422(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    approved_professor_headers: dict,
) -> None:
    contract_id = started_contract["contract_id"]
    _submit_work(client, researcher_headers, contract_id)
    resp = client.post(
        f"/api/v1/professor/reviews/contract/{contract_id}",
        json={"verdict": "pass", "score": 80, "feedback": "Good work overall. The submission met all the required criteria and expectations."},
        headers=approved_professor_headers,
    )
    assert resp.status_code == 422


def test_submission_appears_in_contract_submissions(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
) -> None:
    contract_id = started_contract["contract_id"]
    submission = _submit_work(client, researcher_headers, contract_id)
    sub_id = submission["id"]

    submissions = _get_submissions(client, student_headers, contract_id)
    assert any(s["id"] == sub_id for s in submissions)


def test_review_score_stored_in_professor_analytics(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    approved_professor_headers: dict,
) -> None:
    contract_id = started_contract["contract_id"]
    _submit_work(client, researcher_headers, contract_id)
    client.post(
        f"/api/v1/professor/reviews/contract/{contract_id}",
        json={"verdict": "approved", "score": 92, "feedback": "Outstanding work. The researcher demonstrated exceptional quality and attention to detail."},
        headers=approved_professor_headers,
    )
    analytics = client.get("/api/v1/professor/analytics", headers=approved_professor_headers)
    assert analytics.json()["avg_score_given"] > 0


def test_resubmit_after_revision_creates_new_submission(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    approved_professor_headers: dict,
    student_headers: dict,
) -> None:
    contract_id = started_contract["contract_id"]
    _submit_work(client, researcher_headers, contract_id, notes="Initial submission")

    # Professor requests revision
    client.post(
        f"/api/v1/professor/reviews/contract/{contract_id}",
        json={"verdict": "revision_required", "score": 60, "feedback": "Needs revision. Please address the gaps in the literature review and methodology."},
        headers=approved_professor_headers,
    )

    # Resubmit
    _submit_work(client, researcher_headers, contract_id, notes="Revised submission")

    # Check there are 2 submissions
    submissions = _get_submissions(client, student_headers, contract_id)
    assert len(submissions) == 2


def test_professor_avg_score_given_updated(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    approved_professor_headers: dict,
) -> None:
    contract_id = started_contract["contract_id"]
    _submit_work(client, researcher_headers, contract_id)
    client.post(
        f"/api/v1/professor/reviews/contract/{contract_id}",
        json={"verdict": "approved", "score": 75, "feedback": "Good work overall. The submission met all the required criteria and expectations."},
        headers=approved_professor_headers,
    )
    analytics = client.get("/api/v1/professor/analytics", headers=approved_professor_headers)
    # avg_score_given should be > 0 now
    assert analytics.json()["avg_score_given"] > 0


def test_student_can_approve_submission(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
) -> None:
    contract_id = started_contract["contract_id"]
    _submit_work(client, researcher_headers, contract_id)

    submissions = _get_submissions(client, student_headers, contract_id)
    sub_id = submissions[0]["id"]

    resp = client.post(f"/api/v1/submissions/{sub_id}/approve", headers=student_headers)
    assert resp.status_code == 200
