"""
Performance tests: marketplace at scale.

10 tests verifying the platform handles bulk operations correctly.
"""
from __future__ import annotations

import time
import uuid
import pytest
from fastapi.testclient import TestClient


def _create_job(client, headers, i=0, subject="Computer Science"):
    return client.post(
        "/api/v1/jobs",
        json={
            "title": f"Scale Test Job #{i}",
            "description": f"Performance test job number {i} for scale testing.",
            "subject": subject,
            "academic_level": "Masters",
            "proposed_price": f"{100 + i}.00",
            "deadline": "2099-12-31T00:00:00Z",
        },
        headers=headers,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_create_50_jobs_and_list_within_time_limit(
    client: TestClient, student_headers: dict
) -> None:
    for i in range(50):
        resp = _create_job(client, student_headers, i)
        assert resp.status_code in (200, 201)

    start = time.time()
    resp = client.get("/api/v1/jobs?page_size=50", headers=student_headers)
    elapsed = time.time() - start
    assert resp.status_code == 200
    assert elapsed < 5.0, f"Listing 50 jobs took {elapsed:.2f}s — too slow"


def test_pagination_through_50_jobs(
    client: TestClient, student_headers: dict
) -> None:
    for i in range(50):
        _create_job(client, student_headers, i)

    page1 = client.get("/api/v1/jobs?page=1&page_size=10", headers=student_headers)
    page2 = client.get("/api/v1/jobs?page=2&page_size=10", headers=student_headers)
    page5 = client.get("/api/v1/jobs?page=5&page_size=10", headers=student_headers)

    assert page1.status_code == 200
    assert page2.status_code == 200
    assert page5.status_code == 200

    p1_ids = {j["id"] for j in page1.json()["data"]["items"]}
    p2_ids = {j["id"] for j in page2.json()["data"]["items"]}
    assert not p1_ids.intersection(p2_ids), "Pages should have no overlapping items"


def test_pagination_returns_correct_total(
    client: TestClient, student_headers: dict
) -> None:
    for i in range(15):
        _create_job(client, student_headers, i)

    resp = client.get("/api/v1/jobs?page_size=5", headers=student_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] >= 15
    assert len(data["items"]) == 5


def test_filter_50_jobs_by_subject_returns_correct_subset(
    client: TestClient, student_headers: dict
) -> None:
    # Create 20 jobs with subject=Biology
    for i in range(20):
        _create_job(client, student_headers, i, subject="Biology")
    # Create 10 jobs with subject=Chemistry
    for i in range(10):
        _create_job(client, student_headers, i, subject="Chemistry")

    resp = client.get("/api/v1/jobs?subject=Biology&page_size=50", headers=student_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] >= 20
    for item in data["items"]:
        assert item["subject"] == "Biology"


def test_create_10_bids_for_one_job_all_returned(
    client: TestClient, student_headers: dict, db
) -> None:
    job_resp = _create_job(client, student_headers, 0)
    job_id = job_resp.json()["data"]["id"]

    # Create 10 different researchers
    for i in range(10):
        email = f"perf-r{i}-{uuid.uuid4().hex[:6]}@test.com"
        client.post("/api/v1/auth/register", json={
            "email": email, "password": "TestPassword123!",
            "first_name": f"Researcher{i}", "last_name": "Perf", "role": "researcher"
        })
        login = client.post("/api/v1/auth/login", json={"email": email, "password": "TestPassword123!"})
        r_headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}
        client.post(
            f"/api/v1/jobs/{job_id}/bids",
            json={"proposed_price": f"{90 + i}.00", "message": f"Bid from researcher {i}"},
            headers=r_headers,
        )

    bids_resp = client.get(f"/api/v1/jobs/{job_id}/bids?page_size=50", headers=student_headers)
    assert bids_resp.status_code == 200
    assert bids_resp.json()["data"]["total"] == 10


def test_search_jobs_by_title_returns_results(
    client: TestClient, student_headers: dict
) -> None:
    # Create jobs with specific prefix
    prefix = f"UniqueTitle{uuid.uuid4().hex[:6]}"
    for i in range(5):
        client.post("/api/v1/jobs", json={
            "title": f"{prefix} Job {i}",
            "description": "Search test job created for performance testing.",
            "subject": "Physics", "academic_level": "Bachelors",
            "proposed_price": "100.00", "deadline": "2099-12-31T00:00:00Z"
        }, headers=student_headers)

    resp = client.get(f"/api/v1/jobs?search={prefix}", headers=student_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] >= 5


def test_list_jobs_response_structure(
    client: TestClient, student_headers: dict
) -> None:
    _create_job(client, student_headers, 0)
    resp = client.get("/api/v1/jobs", headers=student_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)


def test_jobs_paginated_correctly_with_page_size_25(
    client: TestClient, student_headers: dict
) -> None:
    for i in range(30):
        _create_job(client, student_headers, i)

    resp = client.get("/api/v1/jobs?page=1&page_size=25", headers=student_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data["items"]) == 25
    assert data["total"] >= 30


def test_jobs_filter_by_academic_level(
    client: TestClient, student_headers: dict
) -> None:
    # Create jobs with specific academic level
    for i in range(5):
        client.post("/api/v1/jobs", json={
            "title": f"PhD Level Job {i}",
            "description": "PhD level test job for filter testing.",
            "subject": "Math", "academic_level": "PhD",
            "proposed_price": "200.00", "deadline": "2099-12-31T00:00:00Z"
        }, headers=student_headers)

    resp = client.get("/api/v1/jobs?academic_level=PhD", headers=student_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] >= 5


def test_many_jobs_admin_listing_works(
    client: TestClient, student_headers: dict, admin_headers: dict
) -> None:
    for i in range(20):
        _create_job(client, student_headers, i)

    resp = client.get("/api/v1/admin/jobs", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] >= 20
