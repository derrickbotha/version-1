"""
Tests for the messaging API endpoints.

GET  /api/v1/conversations
GET  /api/v1/conversations/{id}
GET  /api/v1/conversations/{id}/messages
POST /api/v1/messages

Note: Conversations are created automatically when a researcher places a bid
on a job (via bid_service.place_bid).
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient


def _setup_conversation(client, student_headers, researcher_headers):
    """Create a job, place a bid, accept the bid (which creates a conversation).

    The conversation is created when the student accepts the bid (in accept_bid).
    """
    job_resp = client.post("/api/v1/jobs", json={
        "title": "Messaging Test Job",
        "description": "A job to test messaging between student and researcher.",
        "subject": "Physics",
        "academic_level": "Masters",
        "proposed_price": "200.00",
        "deadline": "2099-12-31T23:59:59Z",
    }, headers=student_headers)
    job_id = job_resp.json()["data"]["id"]

    # Place a bid
    bid_resp = client.post(f"/api/v1/jobs/{job_id}/bids",
                           json={"proposed_price": "180.00", "message": "I can do this."},
                           headers=researcher_headers)
    bid_id = bid_resp.json()["data"]["id"]

    # Accept the bid — this creates the conversation
    client.post(f"/api/v1/bids/{bid_id}/accept", headers=student_headers)

    # Get conversations for student
    conv_resp = client.get("/api/v1/conversations", headers=student_headers)
    conversations = conv_resp.json()["data"]["items"]
    assert len(conversations) >= 1, "No conversation was created after accepting bid"
    return conversations[0]


# ---------------------------------------------------------------------------
# List conversations
# ---------------------------------------------------------------------------

def test_get_conversations_returns_list(client, student_headers, researcher_headers):
    """GET /conversations returns a list after bid is placed."""
    _setup_conversation(client, student_headers, researcher_headers)
    resp = client.get("/api/v1/conversations", headers=student_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "items" in data


def test_get_conversations_requires_auth(client):
    """GET /conversations requires authentication."""
    resp = client.get("/api/v1/conversations")
    assert resp.status_code == 401


def test_researcher_can_see_conversations(client, student_headers, researcher_headers):
    """Researcher can also list their conversations."""
    _setup_conversation(client, student_headers, researcher_headers)
    resp = client.get("/api/v1/conversations", headers=researcher_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "items" in data


def test_empty_conversations_returns_empty_list(client, student_headers):
    """Returns empty list when no conversations exist."""
    resp = client.get("/api/v1/conversations", headers=student_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["items"] == []


# ---------------------------------------------------------------------------
# Get conversation messages
# ---------------------------------------------------------------------------

def test_get_conversation_messages(client, student_headers, researcher_headers):
    """GET /conversations/{id}/messages returns message list."""
    conv = _setup_conversation(client, student_headers, researcher_headers)
    resp = client.get(f"/api/v1/conversations/{conv['id']}/messages",
                      headers=student_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "items" in data
    assert "total" in data


def test_non_participant_cannot_get_messages(client, student_headers, researcher_headers, db):
    """Non-participant cannot get messages from a conversation."""
    from tests.conftest import auth_headers
    other_headers = auth_headers(client, "student")
    conv = _setup_conversation(client, student_headers, researcher_headers)
    resp = client.get(f"/api/v1/conversations/{conv['id']}/messages",
                      headers=other_headers)
    assert resp.status_code == 403


def test_get_messages_requires_auth(client, student_headers, researcher_headers):
    """GET /conversations/{id}/messages requires authentication."""
    conv = _setup_conversation(client, student_headers, researcher_headers)
    resp = client.get(f"/api/v1/conversations/{conv['id']}/messages")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Send message
# ---------------------------------------------------------------------------

def test_participant_can_send_message(client, student_headers, researcher_headers):
    """Conversation participant can send a message."""
    conv = _setup_conversation(client, student_headers, researcher_headers)
    resp = client.post("/api/v1/messages",
                       json={"conversation_id": conv["id"],
                             "content": "Hello, can you start on the research today?"},
                       headers=student_headers)
    assert resp.status_code in (200, 201)


def test_sent_message_appears_in_conversation(client, student_headers, researcher_headers):
    """Sent message appears in conversation message list."""
    conv = _setup_conversation(client, student_headers, researcher_headers)
    client.post("/api/v1/messages",
                json={"conversation_id": conv["id"],
                      "content": "This is a test message."},
                headers=student_headers)
    resp = client.get(f"/api/v1/conversations/{conv['id']}/messages",
                      headers=student_headers)
    items = resp.json()["data"]["items"]
    contents = [m["content"] for m in items]
    assert "This is a test message." in contents


def test_researcher_can_send_message(client, student_headers, researcher_headers):
    """Researcher can also send messages."""
    conv = _setup_conversation(client, student_headers, researcher_headers)
    resp = client.post("/api/v1/messages",
                       json={"conversation_id": conv["id"],
                             "content": "I will start right away!"},
                       headers=researcher_headers)
    assert resp.status_code in (200, 201)


def test_non_participant_cannot_send_message(client, student_headers, researcher_headers, db):
    """Non-participant cannot send messages to a conversation."""
    from tests.conftest import auth_headers
    other_headers = auth_headers(client, "student")
    conv = _setup_conversation(client, student_headers, researcher_headers)
    resp = client.post("/api/v1/messages",
                       json={"conversation_id": conv["id"],
                             "content": "Infiltrating this conversation."},
                       headers=other_headers)
    assert resp.status_code == 403


def test_send_message_requires_auth(client, student_headers, researcher_headers):
    """POST /messages requires authentication."""
    conv = _setup_conversation(client, student_headers, researcher_headers)
    resp = client.post("/api/v1/messages",
                       json={"conversation_id": conv["id"],
                             "content": "No auth."})
    assert resp.status_code == 401
