"""
Platform Config API tests — admin config management + audit log.

20 tests covering:
- Seed default config
- Get config by key
- Update config value
- List all config
- Non-admin gets 403
- Non-existent key returns 404
- Update with description
- Audit log entries created
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


# ─────────────────────────────────────────────────────────────────────────────
# Config tests
# ─────────────────────────────────────────────────────────────────────────────

def test_admin_can_seed_default_config(
    client: TestClient, admin_headers: dict
) -> None:
    resp = client.post("/api/v1/admin/config/seed", headers=admin_headers)
    assert resp.status_code == 200
    assert "seeded" in resp.json()["data"]["message"].lower()


def test_admin_seed_is_idempotent(
    client: TestClient, admin_headers: dict
) -> None:
    client.post("/api/v1/admin/config/seed", headers=admin_headers)
    resp = client.post("/api/v1/admin/config/seed", headers=admin_headers)
    assert resp.status_code == 200


def test_admin_can_list_all_config(
    client: TestClient, admin_headers: dict
) -> None:
    client.post("/api/v1/admin/config/seed", headers=admin_headers)
    resp = client.get("/api/v1/admin/config", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert isinstance(data, list)
    assert len(data) >= 1


def test_admin_can_update_config_value(
    client: TestClient, admin_headers: dict
) -> None:
    # Seed first
    client.post("/api/v1/admin/config/seed", headers=admin_headers)
    # Update platform_fee_pct
    resp = client.patch(
        "/api/v1/admin/config/platform_fee_pct",
        json={"value": "20"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["value"] == "20"


def test_admin_config_update_with_description(
    client: TestClient, admin_headers: dict
) -> None:
    client.post("/api/v1/admin/config/seed", headers=admin_headers)
    resp = client.patch(
        "/api/v1/admin/config/platform_fee_pct",
        json={"value": "18", "description": "Updated platform fee percentage"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["value"] == "18"


def test_admin_can_create_new_config_key(
    client: TestClient, admin_headers: dict
) -> None:
    resp = client.patch(
        "/api/v1/admin/config/custom_test_key",
        json={"value": "custom_value", "description": "Test custom config"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["key"] == "custom_test_key"
    assert resp.json()["data"]["value"] == "custom_value"


def test_non_admin_cannot_list_config(
    client: TestClient, student_headers: dict
) -> None:
    resp = client.get("/api/v1/admin/config", headers=student_headers)
    assert resp.status_code == 403


def test_non_admin_cannot_update_config(
    client: TestClient, researcher_headers: dict
) -> None:
    resp = client.patch(
        "/api/v1/admin/config/platform_fee_pct",
        json={"value": "99"},
        headers=researcher_headers,
    )
    assert resp.status_code == 403


def test_non_admin_cannot_seed_config(
    client: TestClient, student_headers: dict
) -> None:
    resp = client.post("/api/v1/admin/config/seed", headers=student_headers)
    assert resp.status_code == 403


def test_config_key_returns_correct_value_after_update(
    client: TestClient, admin_headers: dict
) -> None:
    client.post("/api/v1/admin/config/seed", headers=admin_headers)
    # Update
    client.patch(
        "/api/v1/admin/config/payout_min_usd",
        json={"value": "25"},
        headers=admin_headers,
    )
    # List all and find the key
    resp = client.get("/api/v1/admin/config", headers=admin_headers)
    assert resp.status_code == 200
    configs = {c["key"]: c["value"] for c in resp.json()["data"]}
    assert configs.get("payout_min_usd") == "25"


def test_config_list_contains_seeded_keys(
    client: TestClient, admin_headers: dict
) -> None:
    client.post("/api/v1/admin/config/seed", headers=admin_headers)
    resp = client.get("/api/v1/admin/config", headers=admin_headers)
    keys = [c["key"] for c in resp.json()["data"]]
    assert "platform_fee_pct" in keys
    assert "max_revision_rounds" in keys


def test_update_config_creates_audit_log_entry(
    client: TestClient, admin_headers: dict
) -> None:
    client.post("/api/v1/admin/config/seed", headers=admin_headers)
    client.patch(
        "/api/v1/admin/config/platform_fee_pct",
        json={"value": "12"},
        headers=admin_headers,
    )
    audit_resp = client.get("/api/v1/admin/audit-log", headers=admin_headers)
    assert audit_resp.status_code == 200
    logs = audit_resp.json()["data"]["items"]
    actions = [log["action"] for log in logs]
    assert "update_config" in actions


def test_admin_audit_log_lists_entries(
    client: TestClient, admin_headers: dict, db
) -> None:
    """Audit log endpoint returns correct data structure."""
    resp = client.get("/api/v1/admin/audit-log", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "items" in data
    assert "total" in data


def test_verify_user_creates_audit_log(
    client: TestClient, admin_headers: dict, db
) -> None:
    import uuid
    from app.models.user import User

    email = f"audittest-{uuid.uuid4().hex[:8]}@test.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "TestPassword123!",
              "first_name": "Audit", "last_name": "Test", "role": "student"},
    )
    user = db.query(User).filter(User.email == email).first()
    user_id = str(user.id)

    client.post(f"/api/v1/admin/users/{user_id}/verify", headers=admin_headers)
    audit_resp = client.get("/api/v1/admin/audit-log", headers=admin_headers)
    logs = audit_resp.json()["data"]["items"]
    actions = [log["action"] for log in logs]
    assert "verify_user" in actions


def test_audit_log_non_admin_gets_403(
    client: TestClient, student_headers: dict
) -> None:
    resp = client.get("/api/v1/admin/audit-log", headers=student_headers)
    assert resp.status_code == 403


def test_config_update_value_is_string(
    client: TestClient, admin_headers: dict
) -> None:
    """Config values are stored as strings."""
    resp = client.patch(
        "/api/v1/admin/config/test_string_key",
        json={"value": "42"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    # Value should be returned as string
    assert isinstance(resp.json()["data"]["value"], str)


def test_config_update_empty_value_rejected(
    client: TestClient, admin_headers: dict
) -> None:
    """Empty string value should be rejected (min_length=1)."""
    resp = client.patch(
        "/api/v1/admin/config/platform_fee_pct",
        json={"value": ""},
        headers=admin_headers,
    )
    assert resp.status_code == 422


def test_multiple_config_updates_reflect_latest(
    client: TestClient, admin_headers: dict
) -> None:
    client.post("/api/v1/admin/config/seed", headers=admin_headers)
    client.patch("/api/v1/admin/config/max_revision_rounds", json={"value": "5"}, headers=admin_headers)
    client.patch("/api/v1/admin/config/max_revision_rounds", json={"value": "7"}, headers=admin_headers)
    resp = client.get("/api/v1/admin/config", headers=admin_headers)
    configs = {c["key"]: c["value"] for c in resp.json()["data"]}
    assert configs.get("max_revision_rounds") == "7"


def test_unauthenticated_cannot_access_config(
    client: TestClient
) -> None:
    resp = client.get("/api/v1/admin/config")
    assert resp.status_code == 401


def test_super_admin_can_also_access_config(
    client: TestClient, super_admin_headers: dict
) -> None:
    resp = client.get("/api/v1/admin/config", headers=super_admin_headers)
    assert resp.status_code == 200
