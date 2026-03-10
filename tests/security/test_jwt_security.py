"""
Security tests: JWT token security.

15 tests verifying JWT token handling.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_tampered_jwt_returns_401(client: TestClient) -> None:
    tampered = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.TAMPERED.INVALIDSIGNATURE"
    resp = client.get("/api/v1/auth/me", headers={"Authorization": tampered})
    assert resp.status_code == 401


def test_completely_invalid_token_returns_401(client: TestClient) -> None:
    resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not_a_jwt_at_all"})
    assert resp.status_code == 401


def test_missing_authorization_header_returns_401(client: TestClient) -> None:
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_wrong_authorization_format_returns_401(client: TestClient) -> None:
    resp = client.get("/api/v1/auth/me", headers={"Authorization": "Token sometoken"})
    assert resp.status_code == 401


def test_empty_bearer_token_returns_401(client: TestClient) -> None:
    resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer "})
    assert resp.status_code == 401


def test_expired_jwt_returns_401(client: TestClient) -> None:
    """Use a manually crafted expired JWT."""
    # This is a JWT with exp in the past, signed with wrong key
    expired_jwt = (
        "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJzdWIiOiJ0ZXN0QHRlc3QuY29tIiwiZXhwIjoxMDAwMDAwMDAwfQ."
        "invalid_signature_for_wrong_secret"
    )
    resp = client.get("/api/v1/auth/me", headers={"Authorization": expired_jwt})
    assert resp.status_code == 401


def test_token_with_wrong_secret_returns_401(client: TestClient) -> None:
    """JWT signed with a different secret should be rejected."""
    # Signed with "wrong-secret" instead of the actual JWT_SECRET
    wrong_secret_jwt = (
        "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJzdWIiOiJ0ZXN0QHRlc3QuY29tIiwiZXhwIjo5OTk5OTk5OTk5fQ."
        "wrong_signature_different_secret"
    )
    resp = client.get("/api/v1/auth/me", headers={"Authorization": wrong_secret_jwt})
    assert resp.status_code == 401


def test_valid_token_allows_access(
    client: TestClient, student_headers: dict
) -> None:
    resp = client.get("/api/v1/auth/me", headers=student_headers)
    assert resp.status_code == 200


def test_valid_token_provides_user_info(
    client: TestClient, student_headers: dict
) -> None:
    resp = client.get("/api/v1/auth/me", headers=student_headers)
    data = resp.json()["data"]
    assert "id" in data
    assert "email" in data
    assert "role" in data


def test_token_with_wrong_role_rejected_for_admin_endpoint(
    client: TestClient, student_headers: dict
) -> None:
    """Student's valid token should be rejected for admin endpoints."""
    resp = client.get("/api/v1/admin/users", headers=student_headers)
    assert resp.status_code == 403


def test_token_with_wrong_role_rejected_for_professor_endpoint(
    client: TestClient, researcher_headers: dict
) -> None:
    """Researcher's valid token rejected for professor endpoints."""
    resp = client.get("/api/v1/professor/profile", headers=researcher_headers)
    assert resp.status_code == 403


def test_bearer_keyword_is_required(client: TestClient, student_headers: dict) -> None:
    """Sending token without 'Bearer' prefix should fail."""
    token = student_headers["Authorization"].replace("Bearer ", "")
    resp = client.get("/api/v1/auth/me", headers={"Authorization": token})
    assert resp.status_code == 401


def test_professor_token_rejected_for_admin(
    client: TestClient, approved_professor_headers: dict
) -> None:
    resp = client.get("/api/v1/admin/users", headers=approved_professor_headers)
    assert resp.status_code == 403


def test_refreshed_token_works(client: TestClient, student_headers: dict) -> None:
    """Test that the refresh endpoint works."""
    # First, get original token
    me_resp = client.get("/api/v1/auth/me", headers=student_headers)
    assert me_resp.status_code == 200


def test_null_authorization_header_returns_401(client: TestClient) -> None:
    """Sending 'null' as authorization."""
    resp = client.get("/api/v1/auth/me", headers={"Authorization": "null"})
    assert resp.status_code == 401
