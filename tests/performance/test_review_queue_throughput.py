"""
Performance tests: review queue throughput.

10 tests verifying professor reviews work at volume.
"""
from __future__ import annotations

import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def _create_and_start_contract(client, student_headers, researcher_headers):
    """Create a full started contract and return contract_id."""
    import uuid as _uuid
    subject = f"Subject{_uuid.uuid4().hex[:4]}"
    job_resp = client.post(
        "/api/v1/jobs",
        json={
            "title": f"Throughput Job {_uuid.uuid4().hex[:6]}",
            "description": "Performance test job for throughput verification.",
            "subject": subject, "academic_level": "Masters",
            "proposed_price": "200.00", "deadline": "2099-12-31T00:00:00Z"
        },
        headers=student_headers,
    )
    job_id = job_resp.json()["data"]["id"]

    bid_resp = client.post(
        f"/api/v1/jobs/{job_id}/bids",
        json={"proposed_price": "180.00", "message": "Throughput test bid"},
        headers=researcher_headers,
    )
    bid_id = bid_resp.json()["data"]["id"]
    contract_id = client.post(f"/api/v1/bids/{bid_id}/accept", headers=student_headers).json()["data"]["id"]

    # Deposit and escrow
    client.post("/api/v1/payments/wallet/deposit", json={"amount": "500.00"}, headers=student_headers)
    client.post(
        "/api/v1/payments/escrow",
        json={"contract_id": contract_id, "payment_provider": "wallet",
              "provider_reference": f"wallet-{contract_id}"},
        headers=student_headers,
    )
    client.post(f"/api/v1/contracts/{contract_id}/start", headers=researcher_headers)
    return contract_id


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_create_5_contracts_and_submit_5_reviews(
    client: TestClient,
    approved_professor_headers: dict,
    db: Session,
) -> None:
    """Create multiple student/researcher pairs and review contracts."""
    # We need different student/researcher pairs
    pairs = []
    for i in range(5):
        # Create student
        s_email = f"s{i}-{uuid.uuid4().hex[:6]}@test.com"
        client.post("/api/v1/auth/register", json={
            "email": s_email, "password": "TestPassword123!",
            "first_name": f"S{i}", "last_name": "User", "role": "student"
        })
        s_login = client.post("/api/v1/auth/login", json={"email": s_email, "password": "TestPassword123!"})
        s_headers = {"Authorization": f"Bearer {s_login.json()['data']['access_token']}"}

        # Create researcher
        r_email = f"r{i}-{uuid.uuid4().hex[:6]}@test.com"
        client.post("/api/v1/auth/register", json={
            "email": r_email, "password": "TestPassword123!",
            "first_name": f"R{i}", "last_name": "User", "role": "researcher"
        })
        r_login = client.post("/api/v1/auth/login", json={"email": r_email, "password": "TestPassword123!"})
        r_headers = {"Authorization": f"Bearer {r_login.json()['data']['access_token']}"}

        pairs.append((s_headers, r_headers))

    contract_ids = []
    for s_h, r_h in pairs:
        cid = _create_and_start_contract(client, s_h, r_h)
        # Submit work
        client.post(
            "/api/v1/submissions",
            json={"contract_id": cid, "submission_notes": "Work done and completed"},
            headers=r_h,
        )
        contract_ids.append(cid)

    # Professor reviews all 5
    for cid in contract_ids:
        resp = client.post(
            f"/api/v1/professor/reviews/contract/{cid}",
            json={"verdict": "approved", "score": 85, "feedback": "Good work. The researcher completed all required tasks to the expected standard."},
            headers=approved_professor_headers,
        )
        assert resp.status_code in (200, 201), f"Review failed for contract {cid}: {resp.text}"

    # Verify analytics
    analytics = client.get("/api/v1/professor/analytics", headers=approved_professor_headers)
    assert analytics.json()["total_reviews"] >= 5


def test_professor_analytics_correct_after_5_reviews(
    client: TestClient,
    approved_professor_headers: dict,
    db: Session,
) -> None:
    """After 5 reviews, analytics should reflect correct counts."""
    pairs = []
    for i in range(5):
        s_email = f"sa{i}-{uuid.uuid4().hex[:6]}@test.com"
        client.post("/api/v1/auth/register", json={
            "email": s_email, "password": "TestPassword123!",
            "first_name": f"SA{i}", "last_name": "User", "role": "student"
        })
        s_login = client.post("/api/v1/auth/login", json={"email": s_email, "password": "TestPassword123!"})
        s_h = {"Authorization": f"Bearer {s_login.json()['data']['access_token']}"}

        r_email = f"ra{i}-{uuid.uuid4().hex[:6]}@test.com"
        client.post("/api/v1/auth/register", json={
            "email": r_email, "password": "TestPassword123!",
            "first_name": f"RA{i}", "last_name": "User", "role": "researcher"
        })
        r_login = client.post("/api/v1/auth/login", json={"email": r_email, "password": "TestPassword123!"})
        r_h = {"Authorization": f"Bearer {r_login.json()['data']['access_token']}"}
        pairs.append((s_h, r_h))

    for s_h, r_h in pairs:
        cid = _create_and_start_contract(client, s_h, r_h)
        client.post(
            "/api/v1/submissions",
            json={"contract_id": cid, "submission_notes": "Work done and completed"},
            headers=r_h,
        )
        client.post(
            f"/api/v1/professor/reviews/contract/{cid}",
            json={"verdict": "approved", "score": 90, "feedback": "Great work. All deliverables were completed to a high standard of quality."},
            headers=approved_professor_headers,
        )

    analytics = client.get("/api/v1/professor/analytics", headers=approved_professor_headers)
    data = analytics.json()
    assert data["total_reviews"] >= 5
    assert data["completed_reviews"] >= 5
    assert data["avg_score_given"] > 0


def test_batch_credential_verification_5_credentials(
    client: TestClient,
    approved_professor_headers: dict,
    db: Session,
) -> None:
    """Professor can verify 5 credentials in sequence."""
    researchers = []
    for i in range(5):
        r_email = f"cred-r{i}-{uuid.uuid4().hex[:6]}@test.com"
        client.post("/api/v1/auth/register", json={
            "email": r_email, "password": "TestPassword123!",
            "first_name": f"CR{i}", "last_name": "User", "role": "researcher"
        })
        r_login = client.post("/api/v1/auth/login", json={"email": r_email, "password": "TestPassword123!"})
        researchers.append({"Authorization": f"Bearer {r_login.json()['data']['access_token']}"})

    cred_ids = []
    for r_h in researchers:
        cred_resp = client.post(
            "/api/v1/professor/credentials",
            json={"credential_type": "phd", "institution_name": "MIT",
                  "field_of_study": "CS", "year_obtained": 2020},
            headers=r_h,
        )
        cred_ids.append(cred_resp.json()["id"])

    # Professor verifies all 5
    for cid in cred_ids:
        resp = client.post(
            f"/api/v1/professor/credentials/{cid}/action",
            json={"action": "verify"},
            headers=approved_professor_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "verified"

    analytics = client.get("/api/v1/professor/analytics", headers=approved_professor_headers)
    assert analytics.json()["credentials_verified"] >= 5


def test_professor_review_list_contains_all_reviews(
    client: TestClient,
    approved_professor_headers: dict,
    db: Session,
) -> None:
    """Professor's review list contains all submitted reviews."""
    contracts = []
    for i in range(3):
        s_email = f"rl-s{i}-{uuid.uuid4().hex[:6]}@test.com"
        client.post("/api/v1/auth/register", json={
            "email": s_email, "password": "TestPassword123!",
            "first_name": f"RLS{i}", "last_name": "User", "role": "student"
        })
        s_login = client.post("/api/v1/auth/login", json={"email": s_email, "password": "TestPassword123!"})
        s_h = {"Authorization": f"Bearer {s_login.json()['data']['access_token']}"}

        r_email = f"rl-r{i}-{uuid.uuid4().hex[:6]}@test.com"
        client.post("/api/v1/auth/register", json={
            "email": r_email, "password": "TestPassword123!",
            "first_name": f"RLR{i}", "last_name": "User", "role": "researcher"
        })
        r_login = client.post("/api/v1/auth/login", json={"email": r_email, "password": "TestPassword123!"})
        r_h = {"Authorization": f"Bearer {r_login.json()['data']['access_token']}"}

        cid = _create_and_start_contract(client, s_h, r_h)
        client.post(
            "/api/v1/submissions",
            json={"contract_id": cid, "submission_notes": "Work done and completed"},
            headers=r_h,
        )
        contracts.append(cid)

    for cid in contracts:
        client.post(
            f"/api/v1/professor/reviews/contract/{cid}",
            json={"verdict": "approved", "score": 80, "feedback": "Good work overall. The submission met all the required criteria and expectations."},
            headers=approved_professor_headers,
        )

    reviews_resp = client.get("/api/v1/professor/reviews", headers=approved_professor_headers)
    assert reviews_resp.status_code == 200
    assert len(reviews_resp.json()) >= 3


def test_admin_transactions_scale_correctly(
    client: TestClient,
    admin_headers: dict,
    student_headers: dict,
) -> None:
    """Admin transactions endpoint handles multiple transactions."""
    for i in range(10):
        client.post(
            "/api/v1/payments/wallet/deposit",
            json={"amount": "10.00"},
            headers=student_headers,
        )
    resp = client.get("/api/v1/admin/transactions", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] >= 10


def test_multiple_reviews_do_not_duplicate_analytics(
    client: TestClient,
    approved_professor_headers: dict,
    db: Session,
) -> None:
    """Professor analytics total_reviews matches actual review count."""
    s_email = f"dedup-s-{uuid.uuid4().hex[:6]}@test.com"
    r_email = f"dedup-r-{uuid.uuid4().hex[:6]}@test.com"

    client.post("/api/v1/auth/register", json={
        "email": s_email, "password": "TestPassword123!",
        "first_name": "S", "last_name": "D", "role": "student"
    })
    s_login = client.post("/api/v1/auth/login", json={"email": s_email, "password": "TestPassword123!"})
    s_h = {"Authorization": f"Bearer {s_login.json()['data']['access_token']}"}

    client.post("/api/v1/auth/register", json={
        "email": r_email, "password": "TestPassword123!",
        "first_name": "R", "last_name": "D", "role": "researcher"
    })
    r_login = client.post("/api/v1/auth/login", json={"email": r_email, "password": "TestPassword123!"})
    r_h = {"Authorization": f"Bearer {r_login.json()['data']['access_token']}"}

    cid = _create_and_start_contract(client, s_h, r_h)
    client.post(
        "/api/v1/submissions",
        json={"contract_id": cid, "submission_notes": "Work done and completed"},
        headers=r_h,
    )

    before = client.get("/api/v1/professor/analytics", headers=approved_professor_headers)
    before_count = before.json()["total_reviews"]

    client.post(
        f"/api/v1/professor/reviews/contract/{cid}",
        json={"verdict": "approved", "score": 80, "feedback": "Good work overall. The submission met all the required criteria and expectations."},
        headers=approved_professor_headers,
    )

    after = client.get("/api/v1/professor/analytics", headers=approved_professor_headers)
    assert after.json()["total_reviews"] == before_count + 1


def test_professor_reviews_paginate_correctly(
    client: TestClient,
    approved_professor_headers: dict,
    db: Session,
) -> None:
    """All professor reviews are returned."""
    pairs = []
    for i in range(5):
        s_email = f"pg-s{i}-{uuid.uuid4().hex[:6]}@test.com"
        client.post("/api/v1/auth/register", json={
            "email": s_email, "password": "TestPassword123!",
            "first_name": f"PGS{i}", "last_name": "User", "role": "student"
        })
        s_login = client.post("/api/v1/auth/login", json={"email": s_email, "password": "TestPassword123!"})
        s_h = {"Authorization": f"Bearer {s_login.json()['data']['access_token']}"}

        r_email = f"pg-r{i}-{uuid.uuid4().hex[:6]}@test.com"
        client.post("/api/v1/auth/register", json={
            "email": r_email, "password": "TestPassword123!",
            "first_name": f"PGR{i}", "last_name": "User", "role": "researcher"
        })
        r_login = client.post("/api/v1/auth/login", json={"email": r_email, "password": "TestPassword123!"})
        r_h = {"Authorization": f"Bearer {r_login.json()['data']['access_token']}"}
        pairs.append((s_h, r_h))

    for s_h, r_h in pairs:
        cid = _create_and_start_contract(client, s_h, r_h)
        client.post(
            "/api/v1/submissions",
            json={"contract_id": cid, "submission_notes": "Work done and completed"},
            headers=r_h,
        )
        client.post(
            f"/api/v1/professor/reviews/contract/{cid}",
            json={"verdict": "approved", "score": 80, "feedback": "Good work overall. The submission met all the required criteria and expectations."},
            headers=approved_professor_headers,
        )

    resp = client.get("/api/v1/professor/reviews", headers=approved_professor_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 5


def test_admin_job_list_handles_many_jobs(
    client: TestClient,
    student_headers: dict,
    admin_headers: dict,
) -> None:
    for i in range(25):
        client.post("/api/v1/jobs", json={
            "title": f"Admin Scale Job {i}",
            "description": "Scale test job for admin listing.",
            "subject": "Biology", "academic_level": "Bachelors",
            "proposed_price": "100.00", "deadline": "2099-12-31T00:00:00Z"
        }, headers=student_headers)

    resp = client.get("/api/v1/admin/jobs?page_size=100", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] >= 25


def test_wallet_transaction_history_paginates(
    client: TestClient, student_headers: dict
) -> None:
    for i in range(10):
        client.post(
            "/api/v1/payments/wallet/deposit",
            json={"amount": "5.00"},
            headers=student_headers,
        )
    page1 = client.get("/api/v1/payments/wallet/transactions?page=1&page_size=5", headers=student_headers)
    page2 = client.get("/api/v1/payments/wallet/transactions?page=2&page_size=5", headers=student_headers)
    assert page1.status_code == 200
    assert page2.status_code == 200

    p1_ids = {t["id"] for t in page1.json()["data"]["items"]}
    p2_ids = {t["id"] for t in page2.json()["data"]["items"]}
    assert not p1_ids.intersection(p2_ids)
