"""
Tests for token refresh and JWT validation.
POST /api/v1/auth/refresh
"""
import base64
import json
import uuid

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _unique_email(prefix: str = "token") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}@example.com"


def _register_and_login(client: TestClient, role: str = "student") -> dict:
    email = _unique_email()
    password = "SecurePass123!"
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": "Token",
            "last_name": "Tester",
            "role": role,
        },
    )
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return resp.json()["data"]


def _decode_jwt_payload(token: str) -> dict:
    """Decode JWT payload without verification."""
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Not a valid JWT structure")
    payload_b64 = parts[1]
    # Add padding
    payload_b64 += "=" * (4 - len(payload_b64) % 4)
    payload_bytes = base64.urlsafe_b64decode(payload_b64)
    return json.loads(payload_bytes)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_refresh_with_valid_refresh_token_returns_new_access_token(client: TestClient) -> None:
    """POST /auth/refresh with valid refresh_token returns a new access_token."""
    auth_data = _register_and_login(client)
    refresh_token = auth_data["refresh_token"]

    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    new_token = resp.json()["data"]["access_token"]
    assert new_token is not None
    assert len(new_token.split(".")) == 3


def test_refresh_with_invalid_token_returns_401(client: TestClient) -> None:
    """POST /auth/refresh with a made-up token returns 401."""
    resp = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "this.is.completely.invalid.token"},
    )
    assert resp.status_code == 401


def test_refresh_with_access_token_returns_401(client: TestClient) -> None:
    """POST /auth/refresh with an access_token (not refresh) returns 401."""
    auth_data = _register_and_login(client)
    access_token = auth_data["access_token"]

    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})
    assert resp.status_code == 401


def test_bearer_token_required_for_protected_endpoints(client: TestClient) -> None:
    """Accessing a protected endpoint without a token returns 401."""
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_token_has_correct_user_id_claim(client: TestClient, db) -> None:
    """JWT payload contains sub claim matching the user's id."""
    from app.models.user import User

    email = _unique_email()
    password = "SecurePass123!"
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": "Claim",
            "last_name": "Tester",
            "role": "student",
        },
    )
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    token = resp.json()["data"]["access_token"]

    payload = _decode_jwt_payload(token)
    user = db.query(User).filter(User.email == email).first()

    # JWT sub should match the user id
    assert payload.get("sub") == str(user.id)


def test_token_has_correct_role_claim(client: TestClient) -> None:
    """JWT payload contains a role claim matching the registered role."""
    email = _unique_email()
    password = "SecurePass123!"
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": "Role",
            "last_name": "Tester",
            "role": "researcher",
        },
    )
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    token = resp.json()["data"]["access_token"]

    payload = _decode_jwt_payload(token)
    assert payload.get("role") == "researcher"


def test_get_me_with_expired_looking_token_returns_401(client: TestClient) -> None:
    """GET /auth/me with a malformed/fake token returns 401."""
    fake_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    headers = {"Authorization": f"Bearer {fake_token}"}
    resp = client.get("/api/v1/auth/me", headers=headers)
    assert resp.status_code == 401
