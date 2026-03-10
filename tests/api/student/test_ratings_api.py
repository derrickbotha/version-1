"""
Tests for the ratings API endpoints.

POST /api/v1/ratings
GET  /api/v1/ratings/contract/{id}
GET  /api/v1/ratings/researcher/{id}
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient


def _complete_contract(client, started_contract, student_headers, researcher_headers):
    """Helper: submit and approve work to complete the contract."""
    sub_resp = client.post("/api/v1/submissions",
                           json={"contract_id": started_contract["contract_id"],
                                 "submission_notes": "All work completed as required."},
                           headers=researcher_headers)
    sub_id = sub_resp.json()["data"]["id"]
    client.post(f"/api/v1/submissions/{sub_id}/approve", headers=student_headers)


def _get_researcher_id(client, researcher_headers):
    resp = client.get("/api/v1/auth/me", headers=researcher_headers)
    return resp.json()["data"]["id"]


# ---------------------------------------------------------------------------
# Create rating
# Note: RatingCreate schema only has contract_id, rating, review (no researcher_id)
# review must be >= 10 chars if provided
# ---------------------------------------------------------------------------

def test_student_can_rate_researcher_after_completed_contract(
    client, student_headers, researcher_headers, started_contract
):
    """Student can rate a researcher after the contract is completed."""
    _complete_contract(client, started_contract, student_headers, researcher_headers)
    resp = client.post("/api/v1/ratings",
                       json={
                           "contract_id": started_contract["contract_id"],
                           "rating": 5,
                           "review": "Excellent work! Very thorough and professional.",
                       },
                       headers=student_headers)
    assert resp.status_code in (200, 201)


def test_rating_response_contains_required_fields(
    client, student_headers, researcher_headers, started_contract
):
    """Rating response contains all required fields."""
    _complete_contract(client, started_contract, student_headers, researcher_headers)
    resp = client.post("/api/v1/ratings",
                       json={
                           "contract_id": started_contract["contract_id"],
                           "rating": 4,
                           "review": "Good research work completed.",
                       },
                       headers=student_headers)
    data = resp.json()["data"]
    assert "id" in data
    assert data["rating"] == 4
    assert data["review"] == "Good research work completed."


def test_rating_must_be_between_1_and_5(
    client, student_headers, researcher_headers, started_contract
):
    """Rating must be 1-5; rating 6 returns 422."""
    _complete_contract(client, started_contract, student_headers, researcher_headers)
    resp = client.post("/api/v1/ratings",
                       json={
                           "contract_id": started_contract["contract_id"],
                           "rating": 6,
                       },
                       headers=student_headers)
    assert resp.status_code == 422


def test_rating_cannot_be_zero(
    client, student_headers, researcher_headers, started_contract
):
    """Rating cannot be 0; returns 422."""
    _complete_contract(client, started_contract, student_headers, researcher_headers)
    resp = client.post("/api/v1/ratings",
                       json={
                           "contract_id": started_contract["contract_id"],
                           "rating": 0,
                       },
                       headers=student_headers)
    assert resp.status_code == 422


def test_cannot_rate_twice_for_same_contract(
    client, student_headers, researcher_headers, started_contract
):
    """Cannot rate the same contract twice (409)."""
    _complete_contract(client, started_contract, student_headers, researcher_headers)
    payload = {
        "contract_id": started_contract["contract_id"],
        "rating": 5,
        "review": "Great work overall!",
    }
    client.post("/api/v1/ratings", json=payload, headers=student_headers)
    resp = client.post("/api/v1/ratings", json=payload, headers=student_headers)
    assert resp.status_code in (400, 409)


def test_researcher_cannot_create_rating(
    client, researcher_headers, student_headers, started_contract
):
    """Researcher cannot create a rating (student only)."""
    _complete_contract(client, started_contract, student_headers, researcher_headers)
    resp = client.post("/api/v1/ratings",
                       json={
                           "contract_id": started_contract["contract_id"],
                           "rating": 5,
                           "review": "Self-rating attempt.",
                       },
                       headers=researcher_headers)
    assert resp.status_code == 403


def test_rating_requires_auth(client, started_contract):
    """Creating a rating requires authentication."""
    resp = client.post("/api/v1/ratings",
                       json={
                           "contract_id": started_contract["contract_id"],
                           "rating": 5,
                       })
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Get rating by contract
# ---------------------------------------------------------------------------

def test_get_rating_by_contract(
    client, student_headers, researcher_headers, started_contract
):
    """Get the rating for a completed+rated contract."""
    _complete_contract(client, started_contract, student_headers, researcher_headers)
    client.post("/api/v1/ratings",
                json={
                    "contract_id": started_contract["contract_id"],
                    "rating": 4,
                    "review": "Good work completed.",
                },
                headers=student_headers)
    resp = client.get(f"/api/v1/ratings/contract/{started_contract['contract_id']}",
                      headers=student_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data is not None
    assert data["rating"] == 4


def test_get_rating_returns_null_when_no_rating(
    client, student_headers, started_contract
):
    """Returns null data when no rating exists for the contract."""
    resp = client.get(f"/api/v1/ratings/contract/{started_contract['contract_id']}",
                      headers=student_headers)
    assert resp.status_code == 200
    assert resp.json()["data"] is None


# ---------------------------------------------------------------------------
# Get ratings for researcher
# ---------------------------------------------------------------------------

def test_get_researcher_ratings(
    client, student_headers, researcher_headers, started_contract
):
    """Get ratings for a researcher."""
    _complete_contract(client, started_contract, student_headers, researcher_headers)
    researcher_id = _get_researcher_id(client, researcher_headers)
    client.post("/api/v1/ratings",
                json={
                    "contract_id": started_contract["contract_id"],
                    "rating": 5,
                    "review": "Outstanding researcher work.",
                },
                headers=student_headers)
    resp = client.get(f"/api/v1/ratings/researcher/{researcher_id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] >= 1


def test_get_researcher_ratings_is_public(client):
    """GET /ratings/researcher/{id} is publicly accessible."""
    resp = client.get(f"/api/v1/ratings/researcher/{uuid.uuid4()}")
    assert resp.status_code == 200
