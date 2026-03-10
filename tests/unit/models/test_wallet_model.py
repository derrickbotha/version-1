"""
Unit tests for the Wallet, WalletTransaction, LedgerAccount, and LedgerEntry models.

Uses direct DB manipulation for model-layer specifics and the API client
where integration-level verification is more appropriate.
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


def _make_user(db: Session, role: str = "student") -> object:
    from app.models.user import User
    from app.services.auth_service import hash_password  # noqa: PLC0415

    u = User(
        id=uuid.uuid4(),
        email=_unique_email(role),
        password_hash=hash_password("TestPassword123!"),
        first_name=role.capitalize(),
        last_name="Tester",
        role=role,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _make_wallet(db: Session, user_id: uuid.UUID, balance: float = 0.0) -> object:
    from app.models.payment import Wallet  # noqa: PLC0415

    w = Wallet(user_id=user_id, balance=balance)
    db.add(w)
    db.commit()
    db.refresh(w)
    return w


def _make_transaction(
    db: Session,
    wallet_id: uuid.UUID,
    amount: float,
    transaction_type: str,
    reference_id: uuid.UUID | None = None,
    notes: str | None = None,
) -> object:
    from app.models.payment import WalletTransaction  # noqa: PLC0415

    tx = WalletTransaction(
        id=uuid.uuid4(),
        wallet_id=wallet_id,
        amount=amount,
        transaction_type=transaction_type,
        reference_id=reference_id,
        notes=notes,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


# ---------------------------------------------------------------------------
# 1. Wallet creation
# ---------------------------------------------------------------------------

class TestWalletCreation:
    def test_wallet_created_with_zero_balance(self, db: Session) -> None:
        user = _make_user(db)
        w = _make_wallet(db, user.id)
        assert float(w.balance) == 0.0

    def test_wallet_user_id_set(self, db: Session) -> None:
        user = _make_user(db)
        w = _make_wallet(db, user.id)
        assert str(w.user_id) == str(user.id)

    def test_wallet_per_user(self, db: Session) -> None:
        u1 = _make_user(db, "student")
        u2 = _make_user(db, "researcher")
        w1 = _make_wallet(db, u1.id)
        w2 = _make_wallet(db, u2.id)
        assert str(w1.user_id) != str(w2.user_id)

    def test_wallet_repr(self, db: Session) -> None:
        user = _make_user(db)
        w = _make_wallet(db, user.id)
        r = repr(w)
        assert "Wallet" in r

    def test_wallet_created_via_register_api(self, client: TestClient, db: Session) -> None:
        from app.models.payment import Wallet  # noqa: PLC0415
        from app.models.user import User  # noqa: PLC0415

        email = _unique_email("walletapi")
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "TestPassword123!",
                "first_name": "Wallet",
                "last_name": "Test",
                "role": "student",
            },
        )
        assert resp.status_code in (200, 201)
        user_id = resp.json()["data"]["id"]
        wallet = db.query(Wallet).filter(
            Wallet.user_id == uuid.UUID(user_id)
        ).first()
        assert wallet is not None
        assert float(wallet.balance) == 0.0


# ---------------------------------------------------------------------------
# 2. Wallet balance update
# ---------------------------------------------------------------------------

class TestWalletBalanceUpdate:
    def test_wallet_balance_update(self, db: Session) -> None:
        user = _make_user(db)
        w = _make_wallet(db, user.id, balance=0.0)
        w.balance = 250.00
        db.commit()
        db.refresh(w)
        assert abs(float(w.balance) - 250.00) < 0.01

    def test_wallet_balance_increment(self, db: Session) -> None:
        user = _make_user(db)
        w = _make_wallet(db, user.id, balance=100.00)
        w.balance = float(w.balance) + 50.00
        db.commit()
        db.refresh(w)
        assert abs(float(w.balance) - 150.00) < 0.01

    def test_wallet_balance_after_api_deposit(
        self, client: TestClient, student_headers: dict
    ) -> None:
        resp = client.post(
            "/api/v1/payments/wallet/deposit",
            json={"amount": "300.00"},
            headers=student_headers,
        )
        assert resp.status_code in (200, 201)
        data = resp.json()["data"]
        assert float(data["balance"]) >= 300.00


# ---------------------------------------------------------------------------
# 3. WalletTransaction types
# ---------------------------------------------------------------------------

class TestWalletTransactionTypes:
    def test_transaction_type_deposit(self, db: Session) -> None:
        user = _make_user(db)
        w = _make_wallet(db, user.id)
        tx = _make_transaction(db, user.id, 100.00, "deposit")
        assert tx.transaction_type == "deposit"

    def test_transaction_type_escrow_lock(self, db: Session) -> None:
        user = _make_user(db)
        w = _make_wallet(db, user.id, balance=200.00)
        tx = _make_transaction(db, user.id, 150.00, "escrow_lock")
        assert tx.transaction_type == "escrow_lock"

    def test_transaction_type_release(self, db: Session) -> None:
        user = _make_user(db)
        w = _make_wallet(db, user.id)
        tx = _make_transaction(db, user.id, 150.00, "release")
        assert tx.transaction_type == "release"

    def test_transaction_type_refund(self, db: Session) -> None:
        user = _make_user(db)
        w = _make_wallet(db, user.id)
        tx = _make_transaction(db, user.id, 75.00, "refund")
        assert tx.transaction_type == "refund"

    def test_transaction_type_payout(self, db: Session) -> None:
        user = _make_user(db)
        w = _make_wallet(db, user.id)
        tx = _make_transaction(db, user.id, 200.00, "payout")
        assert tx.transaction_type == "payout"

    def test_transaction_amount_stored(self, db: Session) -> None:
        user = _make_user(db)
        _make_wallet(db, user.id)
        tx = _make_transaction(db, user.id, 123.45, "deposit")
        assert abs(float(tx.amount) - 123.45) < 0.01

    def test_transaction_repr(self, db: Session) -> None:
        user = _make_user(db)
        _make_wallet(db, user.id)
        tx = _make_transaction(db, user.id, 50.00, "deposit", notes="Test deposit")
        r = repr(tx)
        assert "deposit" in r
        assert "50" in r


# ---------------------------------------------------------------------------
# 4. Multiple transactions per wallet
# ---------------------------------------------------------------------------

class TestMultipleTransactionsPerWallet:
    def test_multiple_transactions_per_wallet(self, db: Session) -> None:
        from app.models.payment import WalletTransaction  # noqa: PLC0415

        user = _make_user(db)
        _make_wallet(db, user.id)
        _make_transaction(db, user.id, 100.00, "deposit")
        _make_transaction(db, user.id, 50.00, "deposit")
        _make_transaction(db, user.id, 30.00, "escrow_lock")

        txs = db.query(WalletTransaction).filter(
            WalletTransaction.wallet_id == user.id
        ).all()
        assert len(txs) == 3

    def test_transaction_with_reference_id(self, db: Session) -> None:
        user = _make_user(db)
        _make_wallet(db, user.id)
        ref = uuid.uuid4()
        tx = _make_transaction(db, user.id, 100.00, "escrow_lock", reference_id=ref)
        assert str(tx.reference_id) == str(ref)

    def test_transaction_notes_stored(self, db: Session) -> None:
        user = _make_user(db)
        _make_wallet(db, user.id)
        tx = _make_transaction(
            db, user.id, 100.00, "deposit",
            notes="Manual deposit from Stripe"
        )
        assert tx.notes == "Manual deposit from Stripe"


# ---------------------------------------------------------------------------
# 5. LedgerAccount types
# ---------------------------------------------------------------------------

class TestLedgerAccountTypes:
    def _make_ledger_account(self, db: Session, account_type: str, user_id=None) -> object:
        from app.models.payment import LedgerAccount  # noqa: PLC0415

        acc = LedgerAccount(
            id=uuid.uuid4(),
            account_type=account_type,
            owner_id=user_id,
            currency="USD",
        )
        db.add(acc)
        db.commit()
        db.refresh(acc)
        return acc

    def test_ledger_account_user_wallet_type(self, db: Session) -> None:
        user = _make_user(db)
        acc = self._make_ledger_account(db, "USER_WALLET", user.id)
        assert acc.account_type == "USER_WALLET"

    def test_ledger_account_escrow_type(self, db: Session) -> None:
        acc = self._make_ledger_account(db, "ESCROW_ACCOUNT")
        assert acc.account_type == "ESCROW_ACCOUNT"

    def test_ledger_account_platform_revenue_type(self, db: Session) -> None:
        acc = self._make_ledger_account(db, "PLATFORM_REVENUE")
        assert acc.account_type == "PLATFORM_REVENUE"

    def test_ledger_account_writer_wallet_type(self, db: Session) -> None:
        user = _make_user(db, "researcher")
        acc = self._make_ledger_account(db, "WRITER_WALLET", user.id)
        assert acc.account_type == "WRITER_WALLET"

    def test_ledger_account_currency_default(self, db: Session) -> None:
        acc = self._make_ledger_account(db, "ESCROW_ACCOUNT")
        assert acc.currency == "USD"

    def test_ledger_account_repr(self, db: Session) -> None:
        acc = self._make_ledger_account(db, "ESCROW_ACCOUNT")
        assert "ESCROW_ACCOUNT" in repr(acc)


# ---------------------------------------------------------------------------
# 6. LedgerEntry debit/credit
# ---------------------------------------------------------------------------

class TestLedgerEntry:
    def _make_ledger_account(self, db: Session, account_type: str = "ESCROW_ACCOUNT") -> object:
        from app.models.payment import LedgerAccount  # noqa: PLC0415

        acc = LedgerAccount(
            id=uuid.uuid4(),
            account_type=account_type,
            currency="USD",
        )
        db.add(acc)
        db.commit()
        db.refresh(acc)
        return acc

    def _make_ledger_entry(
        self,
        db: Session,
        account_id: uuid.UUID,
        debit: float = 0,
        credit: float = 0,
        transaction_ref: str | None = None,
    ) -> object:
        from app.models.payment import LedgerEntry  # noqa: PLC0415

        entry = LedgerEntry(
            id=uuid.uuid4(),
            transaction_ref=transaction_ref or f"TXN-{uuid.uuid4().hex[:8]}",
            account_id=account_id,
            debit=debit,
            credit=credit,
            currency="USD",
            description="Test ledger entry",
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry

    def test_ledger_entry_debit(self, db: Session) -> None:
        acc = self._make_ledger_account(db)
        entry = self._make_ledger_entry(db, acc.id, debit=100.00)
        assert float(entry.debit) == 100.00
        assert float(entry.credit) == 0.00

    def test_ledger_entry_credit(self, db: Session) -> None:
        acc = self._make_ledger_account(db)
        entry = self._make_ledger_entry(db, acc.id, credit=200.00)
        assert float(entry.credit) == 200.00
        assert float(entry.debit) == 0.00

    def test_ledger_entry_one_side_only_constraint_both_nonzero_rejected(
        self, db: Session
    ) -> None:
        """Cannot have both debit > 0 and credit > 0 in the same entry."""
        from app.models.payment import LedgerEntry  # noqa: PLC0415
        from sqlalchemy.exc import IntegrityError  # noqa: PLC0415

        acc = self._make_ledger_account(db)
        entry = LedgerEntry(
            id=uuid.uuid4(),
            transaction_ref="TXN-BOTH",
            account_id=acc.id,
            debit=50.00,
            credit=50.00,
            currency="USD",
        )
        db.add(entry)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    def test_ledger_entry_transaction_ref_stored(self, db: Session) -> None:
        acc = self._make_ledger_account(db)
        entry = self._make_ledger_entry(db, acc.id, debit=75.00, transaction_ref="TXN-REF-001")
        assert entry.transaction_ref == "TXN-REF-001"

    def test_ledger_entry_repr(self, db: Session) -> None:
        acc = self._make_ledger_account(db)
        entry = self._make_ledger_entry(db, acc.id, debit=100.00, transaction_ref="TXN-REPR")
        r = repr(entry)
        assert "TXN-REPR" in r
        assert "100" in r

    def test_ledger_entry_currency_stored(self, db: Session) -> None:
        acc = self._make_ledger_account(db)
        entry = self._make_ledger_entry(db, acc.id, credit=50.00)
        assert entry.currency == "USD"
