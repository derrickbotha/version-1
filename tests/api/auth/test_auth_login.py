"""
Tests for POST /api/v1/auth/login and GET /api/v1/auth/me
"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _unique_email(prefix: str = "login") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}@example.com"


def _register(client: TestClient, email: str, password: str = "SecurePass123!", role: str = "student") -> dict:
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": "Test",
            "last_name": "User",
            "role": role,
        },
    )
    assert resp.status_code in (200, 201), f"Register failed: {resp.text}"
    return resp.json()


def _login(client: TestClient, email: str, password: str) -> dict:
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_valid_credentials_return_200_with_token(client: TestClient) -> None:
    """Valid login returns 200 with access_token."""
    email = _unique_email()
    password = "SecurePass123!"
    _register(client, email, password)

    resp = _login(client, email, password)
    assert resp.status_code == 200
    assert "access_token" in resp.json()["data"]


def test_wrong_password_returns_401(client: TestClient) -> None:
    """Wrong password returns 401."""
    email = _unique_email()
    _register(client, email)

    resp = _login(client, email, "WrongPassword999!")
    assert resp.status_code == 401


def test_nonexistent_email_returns_401(client: TestClient) -> None:
    """Login with non-existent email returns 401."""
    resp = _login(client, "doesnotexist@example.com", "SomePass123!")
    assert resp.status_code == 401


def test_empty_password_returns_error(client: TestClient) -> None:
    """Empty password field returns an error (401 or 422)."""
    resp = client.post("/api/v1/auth/login", json={"email": "a@b.com", "password": ""})
    assert resp.status_code in (401, 422)


def test_empty_email_returns_error(client: TestClient) -> None:
    """Empty email field returns an error (401 or 422)."""
    resp = client.post("/api/v1/auth/login", json={"email": "", "password": "SecurePass123!"})
    assert resp.status_code in (401, 422)


def test_suspended_user_returns_401(client: TestClient, db: Session) -> None:
    """Suspended user cannot log in and receives 401."""
    from app.models.user import User

    email = _unique_email()
    password = "SecurePass123!"
    _register(client, email, password)

    user = db.query(User).filter(User.email == email).first()
    user.status = "suspended"
    db.commit()

    resp = _login(client, email, password)
    assert resp.status_code == 401


def test_deleted_user_returns_401(client: TestClient, db: Session) -> None:
    """Deleted user cannot log in and receives 401."""
    from app.models.user import User

    email = _unique_email()
    password = "SecurePass123!"
    _register(client, email, password)

    user = db.query(User).filter(User.email == email).first()
    user.status = "deleted"
    db.commit()

    resp = _login(client, email, password)
    assert resp.status_code == 401


def test_response_includes_tokens(client: TestClient) -> None:
    """Login response includes access_token and refresh_token."""
    email = _unique_email()
    password = "SecurePass123!"
    _register(client, email, password)

    resp = _login(client, email, password)
    data = resp.json()["data"]
    assert "access_token" in data
    assert "refresh_token" in data


def test_login_token_is_valid_jwt_format(client: TestClient) -> None:
    """Login access_token has three dot-separated JWT parts."""
    email = _unique_email()
    password = "SecurePass123!"
    _register(client, email, password)

    resp = _login(client, email, password)
    token = resp.json()["data"]["access_token"]
    parts = token.split(".")
    assert len(parts) == 3


def test_login_with_same_case_email_works(client: TestClient) -> None:
    """Login with the same email case used at registration succeeds."""
    email = _unique_email()
    password = "SecurePass123!"
    _register(client, email, password)

    resp = _login(client, email, password)
    assert resp.status_code == 200


def test_multiple_logins_work(client: TestClient) -> None:
    """Logging in twice both succeed and return tokens."""
    email = _unique_email()
    password = "SecurePass123!"
    _register(client, email, password)

    resp1 = _login(client, email, password)
    resp2 = _login(client, email, password)
    assert resp1.status_code == 200
    assert resp2.status_code == 200


def test_get_auth_me_with_valid_token_returns_user(client: TestClient) -> None:
    """GET /auth/me with valid token returns user data."""
    email = _unique_email()
    password = "SecurePass123!"
    _register(client, email, password)

    resp = _login(client, email, password)
    token = resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me_resp = client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["data"]["email"].lower() == email.lower()


def test_get_auth_me_without_token_returns_401(client: TestClient) -> None:
    """GET /auth/me without auth token returns 401."""
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_get_auth_me_with_invalid_token_returns_401(client: TestClient) -> None:
    """GET /auth/me with an invalid token returns 401."""
    headers = {"Authorization": "Bearer this.is.invalid"}
    resp = client.get("/api/v1/auth/me", headers=headers)
    assert resp.status_code == 401
