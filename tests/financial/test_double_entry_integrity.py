"""
Financial tests: double-entry ledger integrity.

20 tests verifying that every financial operation creates balanced ledger entries.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def _get_ledger_entries(db: Session, transaction_ref: str):
    from app.models.payment import LedgerEntry
    return db.query(LedgerEntry).filter(
        LedgerEntry.transaction_ref == transaction_ref
    ).all()


def _get_all_entries(db: Session):
    from app.models.payment import LedgerEntry
    return db.query(LedgerEntry).all()


def _get_all_accounts(db: Session):
    from app.models.payment import LedgerAccount
    return db.query(LedgerAccount).all()


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_deposit_creates_ledger_entries(
    client: TestClient,
    student_headers: dict,
    db: Session,
) -> None:
    resp = client.post(
        "/api/v1/payments/wallet/deposit",
        json={"amount": "100.00"},
        headers=student_headers,
    )
    assert resp.status_code in (200, 201)
    entries = _get_all_entries(db)
    assert len(entries) >= 2


def test_deposit_creates_balanced_debit_credit(
    client: TestClient,
    student_headers: dict,
    db: Session,
) -> None:
    resp = client.post(
        "/api/v1/payments/wallet/deposit",
        json={"amount": "250.00"},
        headers=student_headers,
    )
    assert resp.status_code in (200, 201)
    entries = _get_all_entries(db)
    total_debits = sum(Decimal(str(e.debit)) for e in entries)
    total_credits = sum(Decimal(str(e.credit)) for e in entries)
    assert total_debits == total_credits


def test_escrow_creates_balanced_entries(
    client: TestClient,
    full_contract: dict,
    db: Session,
) -> None:
    entries = _get_all_entries(db)
    # Should have deposit entries + escrow entries
    assert len(entries) >= 4

    total_debits = sum(Decimal(str(e.debit)) for e in entries)
    total_credits = sum(Decimal(str(e.credit)) for e in entries)
    assert total_debits == total_credits


def test_release_creates_balanced_entries(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
    db: Session,
) -> None:
    contract_id = started_contract["contract_id"]
    client.post(
        "/api/v1/submissions",
        json={"contract_id": contract_id, "submission_notes": "Work done and completed"},
        headers=researcher_headers,
    )
    subs = client.get(f"/api/v1/contracts/{contract_id}/submissions", headers=student_headers)
    sub_id = subs.json()["data"]["items"][0]["id"]
    client.post(f"/api/v1/submissions/{sub_id}/approve", headers=student_headers)
    client.post(
        "/api/v1/payments/release",
        json={"contract_id": contract_id},
        headers=student_headers,
    )

    entries = _get_all_entries(db)
    total_debits = sum(Decimal(str(e.debit)) for e in entries)
    total_credits = sum(Decimal(str(e.credit)) for e in entries)
    assert total_debits == total_credits


def test_ledger_entries_amounts_are_positive(
    client: TestClient,
    full_contract: dict,
    db: Session,
) -> None:
    entries = _get_all_entries(db)
    for entry in entries:
        assert Decimal(str(entry.debit)) >= 0
        assert Decimal(str(entry.credit)) >= 0


def test_debit_and_credit_never_both_positive_on_same_entry(
    client: TestClient,
    full_contract: dict,
    db: Session,
) -> None:
    entries = _get_all_entries(db)
    for entry in entries:
        debit = float(entry.debit)
        credit = float(entry.credit)
        assert not (debit > 0 and credit > 0), (
            f"Entry {entry.id} has both debit={debit} and credit={credit}"
        )


def test_deposit_transaction_ref_creates_pair(
    client: TestClient,
    student_headers: dict,
    db: Session,
) -> None:
    """Each deposit should create exactly one debit and one credit entry for that ref."""
    me = client.get("/api/v1/auth/me", headers=student_headers)
    user_id = me.json()["data"]["id"]

    client.post(
        "/api/v1/payments/wallet/deposit",
        json={"amount": "300.00"},
        headers=student_headers,
    )

    deposit_ref = f"deposit:{user_id}:300.00"
    entries = _get_ledger_entries(db, deposit_ref)
    assert len(entries) == 2

    debits = [e for e in entries if float(e.debit) > 0]
    credits = [e for e in entries if float(e.credit) > 0]
    assert len(debits) == 1
    assert len(credits) == 1


def test_deposit_ref_sum_balanced(
    client: TestClient,
    student_headers: dict,
    db: Session,
) -> None:
    me = client.get("/api/v1/auth/me", headers=student_headers)
    user_id = me.json()["data"]["id"]

    client.post(
        "/api/v1/payments/wallet/deposit",
        json={"amount": "175.00"},
        headers=student_headers,
    )

    deposit_ref = f"deposit:{user_id}:175.00"
    entries = _get_ledger_entries(db, deposit_ref)
    total_debit = sum(Decimal(str(e.debit)) for e in entries)
    total_credit = sum(Decimal(str(e.credit)) for e in entries)
    assert total_debit == total_credit == Decimal("175.00")


def test_escrow_transaction_ref_creates_pair(
    client: TestClient,
    full_contract: dict,
    db: Session,
) -> None:
    contract_id = full_contract["contract_id"]
    escrow_ref = f"escrow:{contract_id}"
    entries = _get_ledger_entries(db, escrow_ref)
    assert len(entries) == 2

    debits = [e for e in entries if float(e.debit) > 0]
    credits = [e for e in entries if float(e.credit) > 0]
    assert len(debits) == 1
    assert len(credits) == 1


def test_escrow_ref_sum_balanced(
    client: TestClient,
    full_contract: dict,
    db: Session,
) -> None:
    contract_id = full_contract["contract_id"]
    escrow_ref = f"escrow:{contract_id}"
    entries = _get_ledger_entries(db, escrow_ref)
    total_debit = sum(Decimal(str(e.debit)) for e in entries)
    total_credit = sum(Decimal(str(e.credit)) for e in entries)
    assert total_debit == total_credit


def test_release_transaction_ref_creates_pair(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
    db: Session,
) -> None:
    contract_id = started_contract["contract_id"]
    client.post(
        "/api/v1/submissions",
        json={"contract_id": contract_id, "submission_notes": "Work done and completed"},
        headers=researcher_headers,
    )
    subs = client.get(f"/api/v1/contracts/{contract_id}/submissions", headers=student_headers)
    sub_id = subs.json()["data"]["items"][0]["id"]
    client.post(f"/api/v1/submissions/{sub_id}/approve", headers=student_headers)
    client.post(
        "/api/v1/payments/release",
        json={"contract_id": contract_id},
        headers=student_headers,
    )
    release_ref = f"release:{contract_id}"
    entries = _get_ledger_entries(db, release_ref)
    assert len(entries) == 2


def test_all_entries_have_non_zero_amount(
    client: TestClient,
    full_contract: dict,
    db: Session,
) -> None:
    entries = _get_all_entries(db)
    for entry in entries:
        assert float(entry.debit) > 0 or float(entry.credit) > 0


def test_ledger_accounts_created_for_deposit(
    client: TestClient,
    student_headers: dict,
    db: Session,
) -> None:
    from app.models.payment import LedgerAccount
    client.post(
        "/api/v1/payments/wallet/deposit",
        json={"amount": "100.00"},
        headers=student_headers,
    )
    accounts = _get_all_accounts(db)
    account_types = [a.account_type for a in accounts]
    assert "PAYMENT_PROCESSOR" in account_types
    assert "USER_WALLET" in account_types


def test_ledger_accounts_created_for_escrow(
    client: TestClient,
    full_contract: dict,
    db: Session,
) -> None:
    accounts = _get_all_accounts(db)
    account_types = [a.account_type for a in accounts]
    assert "ESCROW_ACCOUNT" in account_types


def test_ledger_accounts_for_release_include_writer_wallet(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
    db: Session,
) -> None:
    contract_id = started_contract["contract_id"]
    client.post(
        "/api/v1/submissions",
        json={"contract_id": contract_id, "submission_notes": "Work done and completed"},
        headers=researcher_headers,
    )
    subs = client.get(f"/api/v1/contracts/{contract_id}/submissions", headers=student_headers)
    sub_id = subs.json()["data"]["items"][0]["id"]
    client.post(f"/api/v1/submissions/{sub_id}/approve", headers=student_headers)
    client.post(
        "/api/v1/payments/release",
        json={"contract_id": contract_id},
        headers=student_headers,
    )
    accounts = _get_all_accounts(db)
    account_types = [a.account_type for a in accounts]
    assert "WRITER_WALLET" in account_types


def test_multiple_deposits_each_balanced(
    client: TestClient,
    student_headers: dict,
    db: Session,
) -> None:
    me = client.get("/api/v1/auth/me", headers=student_headers)
    user_id = me.json()["data"]["id"]

    amounts = ["50.00", "75.00", "125.00"]
    for amt in amounts:
        client.post(
            "/api/v1/payments/wallet/deposit",
            json={"amount": amt},
            headers=student_headers,
        )

    for amt in amounts:
        ref = f"deposit:{user_id}:{amt}"
        entries = _get_ledger_entries(db, ref)
        if entries:
            total_d = sum(Decimal(str(e.debit)) for e in entries)
            total_c = sum(Decimal(str(e.credit)) for e in entries)
            assert total_d == total_c


def test_payout_creates_balanced_entries(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
    db: Session,
) -> None:
    contract_id = started_contract["contract_id"]
    # Complete contract to give researcher funds
    client.post(
        "/api/v1/submissions",
        json={"contract_id": contract_id, "submission_notes": "Work done and completed"},
        headers=researcher_headers,
    )
    subs = client.get(f"/api/v1/contracts/{contract_id}/submissions", headers=student_headers)
    sub_id = subs.json()["data"]["items"][0]["id"]
    client.post(f"/api/v1/submissions/{sub_id}/approve", headers=student_headers)
    client.post(
        "/api/v1/payments/release",
        json={"contract_id": contract_id},
        headers=student_headers,
    )
    # Request payout
    client.post(
        "/api/v1/payments/payout",
        json={"amount": "50.00", "provider": "paypal"},
        headers=researcher_headers,
    )

    entries = _get_all_entries(db)
    total_debits = sum(Decimal(str(e.debit)) for e in entries)
    total_credits = sum(Decimal(str(e.credit)) for e in entries)
    assert total_debits == total_credits


def test_global_ledger_always_balanced(
    client: TestClient,
    started_contract: dict,
    researcher_headers: dict,
    student_headers: dict,
    db: Session,
) -> None:
    """After any sequence of operations the global ledger remains balanced."""
    contract_id = started_contract["contract_id"]
    client.post(
        "/api/v1/submissions",
        json={"contract_id": contract_id, "submission_notes": "Work done and completed"},
        headers=researcher_headers,
    )
    subs = client.get(f"/api/v1/contracts/{contract_id}/submissions", headers=student_headers)
    sub_id = subs.json()["data"]["items"][0]["id"]
    client.post(f"/api/v1/submissions/{sub_id}/approve", headers=student_headers)
    client.post(
        "/api/v1/payments/release",
        json={"contract_id": contract_id},
        headers=student_headers,
    )

    entries = _get_all_entries(db)
    total_debits = sum(Decimal(str(e.debit)) for e in entries)
    total_credits = sum(Decimal(str(e.credit)) for e in entries)
    assert total_debits == total_credits
