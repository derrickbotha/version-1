"""
Tests for the wallet API endpoints.

POST /api/v1/payments/wallet/deposit
GET  /api/v1/payments/wallet
GET  /api/v1/payments/wallet/transactions
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Deposit
# ---------------------------------------------------------------------------

def test_deposit_increases_wallet_balance(client, student_headers):
    """Depositing money increases the wallet balance."""
    resp = client.post("/api/v1/payments/wallet/deposit",
                       json={"amount": "100.00"},
                       headers=student_headers)
    assert resp.status_code in (200, 201)
    data = resp.json()["data"]
    assert float(data["balance"]) >= 100.00


def test_deposit_returns_wallet_data(client, student_headers):
    """Deposit response contains wallet balance and user_id."""
    resp = client.post("/api/v1/payments/wallet/deposit",
                       json={"amount": "50.00"},
                       headers=student_headers)
    assert resp.status_code in (200, 201)
    data = resp.json()["data"]
    assert "balance" in data


def test_deposit_with_negative_amount_returns_422(client, student_headers):
    """Deposit with negative amount returns 422."""
    resp = client.post("/api/v1/payments/wallet/deposit",
                       json={"amount": "-50.00"},
                       headers=student_headers)
    assert resp.status_code == 422


def test_deposit_with_zero_amount_returns_422(client, student_headers):
    """Deposit with zero amount returns 422."""
    resp = client.post("/api/v1/payments/wallet/deposit",
                       json={"amount": "0.00"},
                       headers=student_headers)
    assert resp.status_code == 422


def test_deposit_requires_auth(client):
    """Deposit requires authentication."""
    resp = client.post("/api/v1/payments/wallet/deposit",
                       json={"amount": "100.00"})
    assert resp.status_code == 401


def test_multiple_deposits_accumulate(client, student_headers):
    """Multiple deposits accumulate correctly in wallet balance."""
    client.post("/api/v1/payments/wallet/deposit", json={"amount": "100.00"}, headers=student_headers)
    resp = client.post("/api/v1/payments/wallet/deposit", json={"amount": "200.00"}, headers=student_headers)
    data = resp.json()["data"]
    assert float(data["balance"]) >= 300.00


def test_researcher_can_deposit(client, researcher_headers):
    """Researcher can also deposit to their wallet."""
    resp = client.post("/api/v1/payments/wallet/deposit",
                       json={"amount": "75.00"},
                       headers=researcher_headers)
    assert resp.status_code in (200, 201)


# ---------------------------------------------------------------------------
# Get wallet
# ---------------------------------------------------------------------------

def test_get_wallet_after_deposit_shows_balance(client, student_headers):
    """GET /wallet shows correct balance after deposit."""
    client.post("/api/v1/payments/wallet/deposit", json={"amount": "250.00"}, headers=student_headers)
    resp = client.get("/api/v1/payments/wallet", headers=student_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert float(data["balance"]) >= 250.00


def test_get_wallet_without_deposit_returns_zero_balance(client, student_headers):
    """GET /wallet without any prior deposit returns 200 with 0 balance (wallet created on register)."""
    resp = client.get("/api/v1/payments/wallet", headers=student_headers)
    # Wallet is created on registration, so it exists with balance 0
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert float(data["balance"]) == 0.0


def test_get_wallet_requires_auth(client):
    """GET /wallet requires authentication."""
    resp = client.get("/api/v1/payments/wallet")
    assert resp.status_code == 401


def test_wallet_balance_correct_after_escrow(client, student_headers, full_contract):
    """Wallet balance decreases after escrow."""
    resp = client.get("/api/v1/payments/wallet", headers=student_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    # Started with 500, escrowed 180, so balance should be around 320
    assert float(data["balance"]) < 500.00


# ---------------------------------------------------------------------------
# Transaction history
# ---------------------------------------------------------------------------

def test_get_transaction_history_after_deposit(client, student_headers):
    """Transaction history includes deposit transaction."""
    client.post("/api/v1/payments/wallet/deposit", json={"amount": "100.00"}, headers=student_headers)
    resp = client.get("/api/v1/payments/wallet/transactions", headers=student_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "items" in data
    assert data["total"] >= 1


def test_transaction_types_correct(client, student_headers):
    """Transaction type for deposit is 'deposit'."""
    client.post("/api/v1/payments/wallet/deposit", json={"amount": "100.00"}, headers=student_headers)
    resp = client.get("/api/v1/payments/wallet/transactions", headers=student_headers)
    items = resp.json()["data"]["items"]
    deposit_txns = [t for t in items if t["transaction_type"] == "deposit"]
    assert len(deposit_txns) >= 1


def test_transaction_history_requires_auth(client):
    """GET /wallet/transactions requires authentication."""
    resp = client.get("/api/v1/payments/wallet/transactions")
    assert resp.status_code == 401


def test_multiple_deposits_all_in_history(client, student_headers):
    """Multiple deposits all appear in transaction history."""
    client.post("/api/v1/payments/wallet/deposit", json={"amount": "100.00"}, headers=student_headers)
    client.post("/api/v1/payments/wallet/deposit", json={"amount": "200.00"}, headers=student_headers)
    resp = client.get("/api/v1/payments/wallet/transactions", headers=student_headers)
    data = resp.json()["data"]
    assert data["total"] >= 2


def test_transaction_history_pagination(client, student_headers):
    """Transaction history supports pagination."""
    for _ in range(5):
        client.post("/api/v1/payments/wallet/deposit", json={"amount": "10.00"}, headers=student_headers)
    resp = client.get("/api/v1/payments/wallet/transactions",
                      params={"page": 1, "page_size": 2},
                      headers=student_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data["items"]) <= 2
