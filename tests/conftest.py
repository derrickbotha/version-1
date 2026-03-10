"""
pytest conftest — Research Marketplace Platform test suite.

Strategy
--------
* PostgreSQL-specific types (ARRAY, UUID) are monkey-patched to SQLite
  equivalents BEFORE any model module is imported.
* A single shared SQLite in-memory database is used via StaticPool so the
  same connection is reused across the TestClient's thread pool.
* Tables are created once per session; all rows are deleted between tests
  for isolation (simpler and more reliable than savepoint rollbacks with
  SQLite's threading constraints).
"""
from __future__ import annotations

import uuid
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import JSON, String, create_engine, event, text
from sqlalchemy import types as _sa_types
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# ---------------------------------------------------------------------------
# 1. Patch PostgreSQL types → SQLite equivalents (MUST be first)
# ---------------------------------------------------------------------------
import sqlalchemy.dialects.postgresql as _pg  # noqa: E402


class _SQLiteUUID(_sa_types.TypeDecorator):
    """Stores UUID as VARCHAR(36) for SQLite."""
    impl = String(36)
    cache_ok = True

    def __init__(self, *args, **kwargs):
        super().__init__()

    def process_bind_param(self, value, dialect):
        return str(value) if value is not None else None

    def process_result_value(self, value, dialect):
        try:
            return uuid.UUID(str(value)) if value is not None else None
        except (ValueError, AttributeError):
            return value


_pg.ARRAY = JSON
_pg.UUID = _SQLiteUUID
_pg.JSONB = JSON

# ---------------------------------------------------------------------------
# 2. Create the SQLite test engine (StaticPool = same connection everywhere)
# ---------------------------------------------------------------------------
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_conn, _rec):
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA foreign_keys=OFF")   # FK off so delete order doesn't matter
    cur.close()


TestingSessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

# ---------------------------------------------------------------------------
# 3. Patch production session module so lifespan uses the same SQLite engine
# ---------------------------------------------------------------------------
import app.database.session as _db_session  # noqa: E402

_db_session.engine = engine
_db_session.SessionLocal = TestingSessionLocal

# ---------------------------------------------------------------------------
# 4. Import models + create schema (once per session)
# ---------------------------------------------------------------------------
import app.models.audit_log   # noqa: F401, E402
import app.models.bid         # noqa: F401, E402
import app.models.contract    # noqa: F401, E402
import app.models.job         # noqa: F401, E402
import app.models.message     # noqa: F401, E402
import app.models.payment     # noqa: F401, E402
import app.models.professor   # noqa: F401, E402
import app.models.submission  # noqa: F401, E402
import app.models.user        # noqa: F401, E402

from app.database.base import Base           # noqa: E402
from app.database.session import get_db      # noqa: E402
from app.main import app as fastapi_app      # noqa: E402

Base.metadata.create_all(bind=engine)

# Ordered list of tables for fast deletion between tests
_ALL_TABLES = list(reversed(Base.metadata.sorted_tables))


def _clear_all_tables(conn) -> None:
    """Delete all rows from every table (FK enforcement is off)."""
    for table in _ALL_TABLES:
        conn.execute(table.delete())
    conn.commit()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function", autouse=True)
def _reset_db():
    """Clear all table data and rate-limiter state before every test."""
    with engine.begin() as conn:
        _clear_all_tables(conn)
    # Disable rate limiting entirely for tests so requests aren't throttled
    try:
        from app.routers.auth_router import limiter as _auth_limiter  # noqa: PLC0415
        _auth_limiter.enabled = False
    except Exception:  # noqa: BLE001
        pass
    yield
    # Re-enable after each test (good hygiene even if unused in test suite)
    try:
        _auth_limiter.enabled = True  # type: ignore[possibly-undefined]
    except Exception:  # noqa: BLE001
        pass


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db: Session) -> Generator[TestClient, None, None]:
    def _override_get_db():
        try:
            yield db
        finally:
            pass

    fastapi_app.dependency_overrides[get_db] = _override_get_db
    with TestClient(fastapi_app, raise_server_exceptions=True) as c:
        yield c
    fastapi_app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}@test.com"


def auth_headers(client: TestClient, role: str) -> dict[str, str]:
    email = _unique_email(role)
    password = "TestPassword123!"
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password,
              "first_name": role.capitalize(), "last_name": "User", "role": role},
    )
    assert resp.status_code in (200, 201), f"Register failed ({role}): {resp.text}"
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, f"Login failed ({role}): {login.text}"
    token = login.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def student_headers(client: TestClient) -> dict[str, str]:
    return auth_headers(client, "student")


@pytest.fixture(scope="function")
def researcher_headers(client: TestClient) -> dict[str, str]:
    return auth_headers(client, "researcher")


@pytest.fixture(scope="function")
def admin_headers(client: TestClient, db: Session) -> dict[str, str]:
    from app.models.user import User  # noqa: PLC0415

    email = _unique_email("admin")
    password = "AdminPassword123!"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password,
              "first_name": "Admin", "last_name": "User", "role": "student"},
    )
    user = db.query(User).filter(User.email == email).first()
    if user:
        user.role = "admin"
        db.commit()
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, f"Admin login failed: {login.text}"
    token = login.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def professor_headers(client: TestClient, db) -> dict[str, str]:
    """
    Register a user as student, then promote to professor via DB, and return auth headers.
    The register API only allows student/researcher roles; professors are promoted by admin.
    """
    from app.models.user import User  # noqa: PLC0415

    email = _unique_email("professor")
    password = "TestPassword123!"
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": "Professor",
            "last_name": "User",
            "role": "student",
        },
    )
    assert resp.status_code in (200, 201), f"Register (professor) failed: {resp.text}"
    user = db.query(User).filter(User.email == email).first()
    if user:
        user.role = "professor"
        db.commit()
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, f"Professor login failed: {login.text}"
    token = login.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def approved_professor_headers(
    client: TestClient, admin_headers: dict[str, str], db
) -> dict[str, str]:
    """
    Register a professor, create their profile, and have admin approve it.
    Returns the professor's auth headers.
    """
    from app.models.user import User  # noqa: PLC0415

    email = _unique_email("professor")
    password = "TestPassword123!"
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": "Professor",
            "last_name": "User",
            "role": "student",
        },
    )
    assert resp.status_code in (200, 201), f"Register (approved_professor) failed: {resp.text}"
    user = db.query(User).filter(User.email == email).first()
    if user:
        user.role = "professor"
        db.commit()
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, f"Approved professor login failed: {login.text}"
    token = login.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create professor profile
    profile_resp = client.post(
        "/api/v1/professor/profile",
        json={
            "bio": "Test professor bio",
            "title": "Dr.",
            "department": "Computer Science",
            "expertise_areas": ["ML", "AI"],
            "review_subjects": ["Computer Science"],
        },
        headers=headers,
    )
    assert profile_resp.status_code in (200, 201), (
        f"Create professor profile failed: {profile_resp.text}"
    )
    professor_profile_id = profile_resp.json()["id"]

    # Admin approves the professor
    action_resp = client.post(
        f"/api/v1/admin/professors/{professor_profile_id}/action",
        json={"action": "approve"},
        headers=admin_headers,
    )
    assert action_resp.status_code == 200, (
        f"Approve professor failed: {action_resp.text}"
    )
    return headers


@pytest.fixture(scope="function")
def super_admin_headers(client: TestClient, db) -> dict[str, str]:
    """Register a user and promote them to super_admin, return their auth headers."""
    from app.models.user import User  # noqa: PLC0415

    email = _unique_email("superadmin")
    password = "SuperAdminPassword123!"
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": "Super",
            "last_name": "Admin",
            "role": "student",
        },
    )
    user = db.query(User).filter(User.email == email).first()
    if user:
        user.role = "super_admin"
        db.commit()
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, f"Super admin login failed: {login.text}"
    token = login.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def researcher_id_from_headers(client: TestClient, headers: dict[str, str]) -> str:
    """Return the authenticated user's UUID string given their auth headers."""
    resp = client.get("/api/v1/auth/me", headers=headers)
    assert resp.status_code == 200, f"GET /auth/me failed: {resp.text}"
    return resp.json()["data"]["id"]


@pytest.fixture(scope="function")
def full_contract(
    client: TestClient,
    student_headers: dict[str, str],
    researcher_headers: dict[str, str],
) -> dict:
    """
    Build a contract at status=escrowed:
      student posts job → researcher bids → student accepts →
      student deposits → student escrows.

    Returns {"contract_id": str, "job_id": str, "payment_id": str}.
    """
    # 1. Student posts a job
    job_resp = client.post(
        "/api/v1/jobs",
        json={
            "title": "Full Contract Test Job",
            "description": "A comprehensive test job to exercise the full contract workflow.",
            "subject": "Mathematics",
            "academic_level": "Masters",
            "proposed_price": "200.00",
            "deadline": "2099-12-31T23:59:59Z",
        },
        headers=student_headers,
    )
    assert job_resp.status_code in (200, 201), f"Create job failed: {job_resp.text}"
    job_id = job_resp.json()["data"]["id"]

    # 2. Researcher bids
    bid_resp = client.post(
        f"/api/v1/jobs/{job_id}/bids",
        json={
            "proposed_price": "180.00",
            "message": "I can complete this research task efficiently and thoroughly.",
        },
        headers=researcher_headers,
    )
    assert bid_resp.status_code in (200, 201), f"Place bid failed: {bid_resp.text}"
    bid_id = bid_resp.json()["data"]["id"]

    # 3. Student accepts bid → contract created
    accept_resp = client.post(
        f"/api/v1/bids/{bid_id}/accept",
        headers=student_headers,
    )
    assert accept_resp.status_code == 200, f"Accept bid failed: {accept_resp.text}"
    contract_id = accept_resp.json()["data"]["id"]

    # 4. Student deposits funds
    deposit_resp = client.post(
        "/api/v1/payments/wallet/deposit",
        json={"amount": "500.00"},
        headers=student_headers,
    )
    assert deposit_resp.status_code in (200, 201), f"Deposit failed: {deposit_resp.text}"

    # 5. Student escrows payment
    escrow_resp = client.post(
        "/api/v1/payments/escrow",
        json={
            "contract_id": contract_id,
            "payment_provider": "wallet",
            "provider_reference": f"wallet-{contract_id}",
        },
        headers=student_headers,
    )
    assert escrow_resp.status_code in (200, 201), f"Escrow failed: {escrow_resp.text}"
    payment_id = escrow_resp.json()["data"]["id"]

    return {"contract_id": contract_id, "job_id": job_id, "payment_id": payment_id}


@pytest.fixture(scope="function")
def started_contract(
    client: TestClient,
    full_contract: dict,
    researcher_headers: dict[str, str],
) -> dict:
    """
    Extend full_contract by having the researcher start work.
    Contract status becomes in_progress.

    Returns the same dict as full_contract.
    """
    contract_id = full_contract["contract_id"]
    start_resp = client.post(
        f"/api/v1/contracts/{contract_id}/start",
        headers=researcher_headers,
    )
    assert start_resp.status_code == 200, f"Start contract failed: {start_resp.text}"
    return full_contract


@pytest.fixture(scope="function")
def sample_job(client: TestClient, student_headers: dict[str, str]) -> dict:
    resp = client.post(
        "/api/v1/jobs",
        json={
            "title": "Sample Research Job",
            "description": "This is a sample research job created for testing purposes.",
            "subject": "Computer Science",
            "academic_level": "Masters",
            "proposed_price": "150.00",
            "deadline": "2099-12-31T23:59:59Z",
        },
        headers=student_headers,
    )
    assert resp.status_code in (200, 201), f"Create sample job failed: {resp.text}"
    return resp.json()["data"]
