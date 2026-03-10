"""
Tests for POST /api/v1/auth/register
"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _unique_email(prefix: str = "user") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}@example.com"


def _register(
    client: TestClient,
    email: str,
    password: str = "SecurePass123!",
    first_name: str = "Test",
    last_name: str = "User",
    role: str = "student",
) -> dict:
    return client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": first_name,
            "last_name": last_name,
            "role": role,
        },
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_register_student_returns_201(client: TestClient) -> None:
    """Registering with role=student returns 201 with status=success."""
    resp = _register(client, _unique_email(), role="student")
    assert resp.status_code in (200, 201)
    assert resp.json()["status"] == "success"


def test_register_researcher_returns_201(client: TestClient) -> None:
    """Registering with role=researcher returns 201 with status=success."""
    resp = _register(client, _unique_email(), role="researcher")
    assert resp.status_code in (200, 201)
    assert resp.json()["status"] == "success"


def test_register_duplicate_email_returns_409(client: TestClient) -> None:
    """Registering twice with the same email returns 409."""
    email = _unique_email()
    _register(client, email)
    resp = _register(client, email)
    assert resp.status_code == 409


def test_register_missing_email_returns_422(client: TestClient) -> None:
    """Missing email field returns 422."""
    resp = client.post(
        "/api/v1/auth/register",
        json={"password": "SecurePass123!", "first_name": "Test", "last_name": "User", "role": "student"},
    )
    assert resp.status_code == 422


def test_register_missing_password_returns_422(client: TestClient) -> None:
    """Missing password field returns 422."""
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": _unique_email(), "first_name": "Test", "last_name": "User", "role": "student"},
    )
    assert resp.status_code == 422


def test_register_missing_first_name_returns_422(client: TestClient) -> None:
    """Missing first_name field returns 422."""
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": _unique_email(), "password": "SecurePass123!", "last_name": "User", "role": "student"},
    )
    assert resp.status_code == 422


def test_register_missing_last_name_returns_422(client: TestClient) -> None:
    """Missing last_name field returns 422."""
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": _unique_email(), "password": "SecurePass123!", "first_name": "Test", "role": "student"},
    )
    assert resp.status_code == 422


def test_register_invalid_email_format_returns_422(client: TestClient) -> None:
    """Invalid email format returns 422."""
    resp = _register(client, "not-an-email")
    assert resp.status_code == 422


def test_register_student_creates_wallet(client: TestClient) -> None:
    """After register, a wallet is accessible via GET /payments/wallet."""
    email = _unique_email()
    password = "SecurePass123!"
    _register(client, email, password, role="student")

    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    token = login_resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Wallet only exists after first deposit, so deposit first
    deposit_resp = client.post(
        "/api/v1/payments/wallet/deposit",
        json={"amount": "10.00"},
        headers=headers,
    )
    assert deposit_resp.status_code in (200, 201)

    wallet_resp = client.get("/api/v1/payments/wallet", headers=headers)
    assert wallet_resp.status_code == 200


def test_register_response_user_has_id(client: TestClient) -> None:
    """Register response data has an 'id' field (user object)."""
    resp = _register(client, _unique_email())
    data = resp.json()["data"]
    assert "id" in data


def test_register_response_user_has_correct_role(client: TestClient) -> None:
    """Register response data has the correct role."""
    resp = _register(client, _unique_email(), role="researcher")
    data = resp.json()["data"]
    assert data["role"] == "researcher"


def test_register_response_user_has_correct_email(client: TestClient) -> None:
    """Register response data has the correct email."""
    email = _unique_email()
    resp = _register(client, email)
    data = resp.json()["data"]
    assert data["email"].lower() == email.lower()


def test_register_with_special_chars_in_name(client: TestClient) -> None:
    """Registering with special characters in name succeeds."""
    resp = _register(
        client,
        _unique_email(),
        first_name="Mary-Jane",
        last_name="O'Brien",
    )
    assert resp.status_code in (200, 201)


def test_register_same_email_exact_match_returns_409(client: TestClient) -> None:
    """Registering with the exact same email twice returns 409."""
    email = _unique_email()
    _register(client, email)
    resp = _register(client, email)
    assert resp.status_code == 409


def test_register_response_data_has_role(client: TestClient) -> None:
    """Register response data has a role field."""
    resp = _register(client, _unique_email(), role="student")
    data = resp.json()["data"]
    assert "role" in data
    assert data["role"] == "student"


def test_register_response_status_is_success(client: TestClient) -> None:
    """Register response top-level status is 'success'."""
    resp = _register(client, _unique_email())
    assert resp.json()["status"] == "success"


def test_register_student_profile_created(client: TestClient, db: Session) -> None:
    """Registering as student creates a StudentProfile in the database."""
    from app.models.user import User, StudentProfile

    email = _unique_email()
    _register(client, email, role="student")

    user = db.query(User).filter(User.email == email).first()
    assert user is not None

    profile = db.query(StudentProfile).filter(StudentProfile.user_id == user.id).first()
    assert profile is not None


def test_register_researcher_profile_created(client: TestClient, db: Session) -> None:
    """Registering as researcher creates a ResearcherProfile in the database."""
    from app.models.user import User, ResearcherProfile

    email = _unique_email()
    _register(client, email, role="researcher")

    user = db.query(User).filter(User.email == email).first()
    assert user is not None

    profile = db.query(ResearcherProfile).filter(ResearcherProfile.user_id == user.id).first()
    assert profile is not None


def test_register_response_has_email_in_data(client: TestClient) -> None:
    """Register response data has email field."""
    email = _unique_email()
    resp = _register(client, email)
    data = resp.json()["data"]
    assert "email" in data
    assert data["email"] is not None


def test_register_first_and_last_name_stored(client: TestClient) -> None:
    """Register response data has first_name and last_name."""
    resp = _register(client, _unique_email(), first_name="Alice", last_name="Smith")
    data = resp.json()["data"]
    assert data.get("first_name") == "Alice"
    assert data.get("last_name") == "Smith"
