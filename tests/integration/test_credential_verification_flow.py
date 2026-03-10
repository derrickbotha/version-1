"""
Integration tests: researcher submits credential → professor verifies.

10 tests:
- Researcher submits credential
- Credential appears in professor's pending queue
- Professor verifies credential
- Credential status becomes verified
- Professor rejects credential with reason
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def _submit_credential(client, researcher_headers):
    resp = client.post(
        "/api/v1/professor/credentials",
        json={
            "credential_type": "phd",
            "institution_name": "MIT",
            "field_of_study": "Computer Science",
            "year_obtained": 2020,
            "notes": "PhD in AI and Machine Learning",
        },
        headers=researcher_headers,
    )
    assert resp.status_code in (200, 201), resp.text
    return resp.json()


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_researcher_can_submit_credential(
    client: TestClient,
    researcher_headers: dict,
) -> None:
    cred = _submit_credential(client, researcher_headers)
    assert cred["id"] is not None
    assert cred["status"] == "pending"


def test_credential_appears_in_professor_pending_queue(
    client: TestClient,
    researcher_headers: dict,
    approved_professor_headers: dict,
) -> None:
    cred = _submit_credential(client, researcher_headers)
    resp = client.get(
        "/api/v1/professor/credentials/pending",
        headers=approved_professor_headers,
    )
    assert resp.status_code == 200
    cred_ids = [c["id"] for c in resp.json()]
    assert cred["id"] in cred_ids


def test_professor_verifies_credential(
    client: TestClient,
    researcher_headers: dict,
    approved_professor_headers: dict,
) -> None:
    cred = _submit_credential(client, researcher_headers)
    resp = client.post(
        f"/api/v1/professor/credentials/{cred['id']}/action",
        json={"action": "verify"},
        headers=approved_professor_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "verified"


def test_credential_status_becomes_verified(
    client: TestClient,
    researcher_headers: dict,
    approved_professor_headers: dict,
) -> None:
    cred = _submit_credential(client, researcher_headers)
    client.post(
        f"/api/v1/professor/credentials/{cred['id']}/action",
        json={"action": "verify"},
        headers=approved_professor_headers,
    )
    # Check researcher's credentials
    researcher_resp = client.get("/api/v1/auth/me", headers=researcher_headers)
    researcher_id = researcher_resp.json()["data"]["id"]
    creds_resp = client.get(
        f"/api/v1/professor/credentials/researcher/{researcher_id}",
        headers=researcher_headers,
    )
    creds = creds_resp.json()
    verified = [c for c in creds if c["id"] == cred["id"]]
    assert verified[0]["status"] == "verified"


def test_professor_rejects_credential_with_reason(
    client: TestClient,
    researcher_headers: dict,
    approved_professor_headers: dict,
) -> None:
    cred = _submit_credential(client, researcher_headers)
    resp = client.post(
        f"/api/v1/professor/credentials/{cred['id']}/action",
        json={"action": "reject", "rejection_reason": "Document is not legible and cannot be verified"},
        headers=approved_professor_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"
    assert resp.json()["rejection_reason"] is not None


def test_credential_not_in_pending_queue_after_verification(
    client: TestClient,
    researcher_headers: dict,
    approved_professor_headers: dict,
) -> None:
    cred = _submit_credential(client, researcher_headers)
    client.post(
        f"/api/v1/professor/credentials/{cred['id']}/action",
        json={"action": "verify"},
        headers=approved_professor_headers,
    )
    pending_resp = client.get(
        "/api/v1/professor/credentials/pending",
        headers=approved_professor_headers,
    )
    cred_ids = [c["id"] for c in pending_resp.json()]
    assert cred["id"] not in cred_ids


def test_reject_credential_without_reason_returns_422(
    client: TestClient,
    researcher_headers: dict,
    approved_professor_headers: dict,
) -> None:
    cred = _submit_credential(client, researcher_headers)
    resp = client.post(
        f"/api/v1/professor/credentials/{cred['id']}/action",
        json={"action": "reject"},  # Missing rejection_reason
        headers=approved_professor_headers,
    )
    assert resp.status_code == 422


def test_cannot_verify_already_verified_credential(
    client: TestClient,
    researcher_headers: dict,
    approved_professor_headers: dict,
) -> None:
    cred = _submit_credential(client, researcher_headers)
    client.post(
        f"/api/v1/professor/credentials/{cred['id']}/action",
        json={"action": "verify"},
        headers=approved_professor_headers,
    )
    # Try to verify again — should fail with 409
    resp = client.post(
        f"/api/v1/professor/credentials/{cred['id']}/action",
        json={"action": "verify"},
        headers=approved_professor_headers,
    )
    assert resp.status_code == 409


def test_student_cannot_submit_credential(
    client: TestClient,
    student_headers: dict,
) -> None:
    resp = client.post(
        "/api/v1/professor/credentials",
        json={"credential_type": "phd", "institution_name": "MIT"},
        headers=student_headers,
    )
    assert resp.status_code == 403


def test_credentials_analytics_count_updates(
    client: TestClient,
    researcher_headers: dict,
    approved_professor_headers: dict,
) -> None:
    cred = _submit_credential(client, researcher_headers)
    client.post(
        f"/api/v1/professor/credentials/{cred['id']}/action",
        json={"action": "verify"},
        headers=approved_professor_headers,
    )
    analytics = client.get("/api/v1/professor/analytics", headers=approved_professor_headers)
    assert analytics.json()["credentials_verified"] >= 1
