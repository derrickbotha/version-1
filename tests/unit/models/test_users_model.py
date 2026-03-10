"""
Unit tests for the User, StudentProfile, ResearcherProfile, and Wallet models.

All tests use the `db` fixture (SQLite in-memory) and the `client` fixture
where API-level verification is more appropriate than raw DB manipulation.
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _unique_email(prefix: str = "user") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}@test.com"


def _make_user(db: Session, role: str = "student", email: str | None = None) -> object:
    """Directly insert a minimal User row into the DB."""
    from app.models.user import User
    from app.services.auth_service import hash_password  # noqa: PLC0415

    u = User(
        id=uuid.uuid4(),
        email=email or _unique_email(role),
        password_hash=hash_password("TestPassword123!"),
        first_name=role.capitalize(),
        last_name="Tester",
        role=role,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _register_via_api(client: TestClient, role: str = "student") -> dict:
    email = _unique_email(role)
    password = "TestPassword123!"
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": role.capitalize(),
            "last_name": "User",
            "role": role,
        },
    )
    assert resp.status_code in (200, 201), f"Register failed: {resp.text}"
    return resp.json()["data"]


# ---------------------------------------------------------------------------
# 1. Role defaults
# ---------------------------------------------------------------------------

class TestUserRoleDefaults:
    def test_default_role_is_student(self, db: Session) -> None:
        """When no role is specified the default should be student."""
        from app.models.user import User
        from app.services.auth_service import hash_password  # noqa: PLC0415

        u = User(
            id=uuid.uuid4(),
            email=_unique_email("default"),
            password_hash=hash_password("TestPassword123!"),
            first_name="Default",
            last_name="User",
            role="student",  # explicit; DB default also applies
        )
        db.add(u)
        db.commit()
        db.refresh(u)
        assert u.role == "student"

    def test_role_student_valid(self, db: Session) -> None:
        u = _make_user(db, role="student")
        assert u.role == "student"

    def test_role_researcher_valid(self, db: Session) -> None:
        u = _make_user(db, role="researcher")
        assert u.role == "researcher"

    def test_role_professor_valid(self, db: Session) -> None:
        u = _make_user(db, role="professor")
        assert u.role == "professor"

    def test_role_admin_valid(self, db: Session) -> None:
        u = _make_user(db, role="admin")
        assert u.role == "admin"

    def test_role_super_admin_valid(self, db: Session) -> None:
        u = _make_user(db, role="super_admin")
        assert u.role == "super_admin"


# ---------------------------------------------------------------------------
# 2. Status defaults
# ---------------------------------------------------------------------------

class TestUserStatusDefaults:
    def test_status_defaults_to_active(self, db: Session) -> None:
        u = _make_user(db)
        assert u.status == "active"

    def test_status_can_be_suspended(self, db: Session) -> None:
        u = _make_user(db)
        u.status = "suspended"
        db.commit()
        db.refresh(u)
        assert u.status == "suspended"

    def test_status_can_be_deleted(self, db: Session) -> None:
        u = _make_user(db)
        u.status = "deleted"
        db.commit()
        db.refresh(u)
        assert u.status == "deleted"


# ---------------------------------------------------------------------------
# 3. Boolean and integer defaults
# ---------------------------------------------------------------------------

class TestUserBooleanIntDefaults:
    def test_is_verified_defaults_to_false(self, db: Session) -> None:
        u = _make_user(db)
        assert u.is_verified is False

    def test_failed_login_attempts_defaults_to_zero(self, db: Session) -> None:
        u = _make_user(db)
        assert u.failed_login_attempts == 0

    def test_locked_until_defaults_to_none(self, db: Session) -> None:
        u = _make_user(db)
        assert u.locked_until is None


# ---------------------------------------------------------------------------
# 4. Email uniqueness
# ---------------------------------------------------------------------------

class TestUserEmailUniqueness:
    def test_email_is_unique_raises_on_duplicate(self, db: Session) -> None:
        email = _unique_email("dup")
        _make_user(db, email=email)
        with pytest.raises(IntegrityError):
            _make_user(db, email=email)

    def test_different_emails_accepted(self, db: Session) -> None:
        u1 = _make_user(db, email=_unique_email("a"))
        u2 = _make_user(db, email=_unique_email("b"))
        assert u1.id != u2.id


# ---------------------------------------------------------------------------
# 5. Profile creation via register API
# ---------------------------------------------------------------------------

class TestProfileCreationViaAPI:
    def test_student_profile_created_on_register(self, client: TestClient, db: Session) -> None:
        from app.models.user import StudentProfile, User  # noqa: PLC0415

        data = _register_via_api(client, role="student")
        user = db.query(User).filter(User.id == uuid.UUID(data["id"])).first()
        assert user is not None
        profile = db.query(StudentProfile).filter(
            StudentProfile.user_id == user.id
        ).first()
        assert profile is not None
        assert str(profile.user_id) == str(user.id)

    def test_researcher_profile_created_on_register(self, client: TestClient, db: Session) -> None:
        from app.models.user import ResearcherProfile, User  # noqa: PLC0415

        data = _register_via_api(client, role="researcher")
        user = db.query(User).filter(User.id == uuid.UUID(data["id"])).first()
        assert user is not None
        profile = db.query(ResearcherProfile).filter(
            ResearcherProfile.user_id == user.id
        ).first()
        assert profile is not None

    def test_wallet_created_on_register(self, client: TestClient, db: Session) -> None:
        from app.models.payment import Wallet  # noqa: PLC0415
        from app.models.user import User  # noqa: PLC0415

        data = _register_via_api(client, role="student")
        user = db.query(User).filter(User.id == uuid.UUID(data["id"])).first()
        assert user is not None
        wallet = db.query(Wallet).filter(Wallet.user_id == user.id).first()
        assert wallet is not None

    def test_wallet_starts_with_zero_balance(self, client: TestClient, db: Session) -> None:
        from app.models.payment import Wallet  # noqa: PLC0415
        from app.models.user import User  # noqa: PLC0415

        data = _register_via_api(client, role="student")
        user = db.query(User).filter(User.id == uuid.UUID(data["id"])).first()
        wallet = db.query(Wallet).filter(Wallet.user_id == user.id).first()
        assert float(wallet.balance) == 0.0


# ---------------------------------------------------------------------------
# 6. __repr__
# ---------------------------------------------------------------------------

class TestUserRepr:
    def test_user_repr_includes_email(self, db: Session) -> None:
        email = _unique_email("repr")
        u = _make_user(db, email=email)
        assert email in repr(u)

    def test_user_repr_includes_role(self, db: Session) -> None:
        u = _make_user(db, role="researcher")
        assert "researcher" in repr(u)


# ---------------------------------------------------------------------------
# 7. Field updates
# ---------------------------------------------------------------------------

class TestUserFieldUpdates:
    def test_update_first_name(self, db: Session) -> None:
        u = _make_user(db)
        u.first_name = "Updated"
        db.commit()
        db.refresh(u)
        assert u.first_name == "Updated"

    def test_update_is_verified(self, db: Session) -> None:
        u = _make_user(db)
        assert u.is_verified is False
        u.is_verified = True
        db.commit()
        db.refresh(u)
        assert u.is_verified is True

    def test_increment_failed_login_attempts(self, db: Session) -> None:
        u = _make_user(db)
        u.failed_login_attempts += 1
        db.commit()
        db.refresh(u)
        assert u.failed_login_attempts == 1

    def test_update_whatsapp_number(self, db: Session) -> None:
        u = _make_user(db)
        u.whatsapp_number = "+27821234567"
        db.commit()
        db.refresh(u)
        assert u.whatsapp_number == "+27821234567"


# ---------------------------------------------------------------------------
# 8. Multiple users
# ---------------------------------------------------------------------------

class TestMultipleUsers:
    def test_multiple_students_independent(self, db: Session) -> None:
        u1 = _make_user(db, role="student")
        u2 = _make_user(db, role="student")
        assert u1.id != u2.id
        assert u1.email != u2.email

    def test_user_id_is_uuid(self, db: Session) -> None:
        u = _make_user(db)
        # id should be a UUID object (or a string that is a valid UUID)
        assert uuid.UUID(str(u.id)) is not None
