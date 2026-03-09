"""
Tests for the authentication endpoints:
  POST /api/v1/auth/register
  POST /api/v1/auth/login
  POST /api/v1/auth/refresh
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _unique_email() -> str:
    return f"user-{uuid.uuid4().hex[:8]}@example.com"


def _register(client: TestClient, email: str, password: str = "SecurePass123!", role: str = "student") -> dict:
    return client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": "Test",
            "last_name": "User",
            "role": role,
        },
    )


def _login(client: TestClient, email: str, password: str) -> dict:
    return client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )


# ---------------------------------------------------------------------------
# Registration tests
# ---------------------------------------------------------------------------

def test_register_student(client: TestClient) -> None:
    """Registering with role=student returns 201 and status=success."""
    email = _unique_email()
    resp = _register(client, email, role="student")
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "success"
    data = body["data"]
    assert data["email"] == email
    assert data["role"] == "student"
    assert "id" in data


def test_register_researcher(client: TestClient) -> None:
    """Registering with role=researcher returns 201."""
    email = _unique_email()
    resp = _register(client, email, role="researcher")
    assert resp.status_code == 201
    assert resp.json()["data"]["role"] == "researcher"


def test_register_duplicate_email(client: TestClient) -> None:
    """Attempting to register with an already-used email returns 409."""
    email = _unique_email()
    _register(client, email)  # first registration — should succeed
    resp = _register(client, email)  # duplicate — should fail
    assert resp.status_code == 409


def test_register_weak_password(client: TestClient) -> None:
    """Password shorter than 10 characters fails schema validation with 422."""
    resp = _register(client, _unique_email(), password="short")
    assert resp.status_code == 422


def test_register_missing_fields(client: TestClient) -> None:
    """Omitting required fields returns 422."""
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": _unique_email()},  # missing password, first_name, last_name
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Login tests
# ---------------------------------------------------------------------------

def test_login_success(client: TestClient) -> None:
    """Valid credentials return 200 with access_token and refresh_token."""
    email = _unique_email()
    password = "ValidPass999!"
    _register(client, email, password=password)

    resp = _login(client, email, password)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client: TestClient) -> None:
    """Wrong password returns 401."""
    email = _unique_email()
    _register(client, email, password="CorrectPass123!")

    resp = _login(client, email, "WrongPass999!")
    assert resp.status_code == 401


def test_login_unknown_email(client: TestClient) -> None:
    """Logging in with an email that was never registered returns 401."""
    resp = _login(client, "nobody@nowhere.example.com", "SomePass123!")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Token refresh
# ---------------------------------------------------------------------------

def test_refresh_token(client: TestClient) -> None:
    """Exchanging a valid refresh token returns new access and refresh tokens."""
    email = _unique_email()
    password = "RefreshPass123!"
    _register(client, email, password=password)
    login_data = _login(client, email, password).json()["data"]
    refresh_token = login_data["refresh_token"]

    resp = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert resp.status_code == 200
    new_data = resp.json()["data"]
    assert "access_token" in new_data
    assert new_data["access_token"] != login_data["access_token"]


def test_refresh_with_access_token_fails(client: TestClient) -> None:
    """Using an access token as a refresh token should return 401."""
    email = _unique_email()
    password = "RefreshFail123!"
    _register(client, email, password=password)
    login_data = _login(client, email, password).json()["data"]
    access_token = login_data["access_token"]

    resp = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": access_token},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Account lockout
# ---------------------------------------------------------------------------

def test_account_lockout(client: TestClient) -> None:
    """
    After 5 consecutive failed login attempts the account is locked.
    The 6th attempt should return a message indicating the account is locked.
    """
    email = _unique_email()
    password = "LockoutPass123!"
    _register(client, email, password=password)

    # Trigger 5 failed login attempts
    for _ in range(5):
        resp = _login(client, email, "WrongPass999!")
        assert resp.status_code == 401

    # The 6th attempt — account should now be locked
    resp = _login(client, email, "WrongPass999!")
    assert resp.status_code == 401
    message: str = resp.json().get("message", "").lower()
    assert "lock" in message or "attempt" in message or "temporarily" in message
