"""
Double-entry ledger service.

Every financial event posts a balanced pair of LedgerEntry rows
(debit on one account, credit on another).  SUM(debits) == SUM(credits)
is maintained by always calling post_entry() for both sides together.

Spec §4.4, §4.5, §6.
"""
from __future__ import annotations

import logging
import uuid
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.payment import LedgerAccount, LedgerEntry

logger = logging.getLogger(__name__)


def _get_or_create_account(
    db: Session,
    account_type: str,
    owner_id: uuid.UUID | None = None,
    currency: str = "USD",
) -> LedgerAccount:
    q = db.query(LedgerAccount).filter(LedgerAccount.account_type == account_type)
    if owner_id is not None:
        q = q.filter(LedgerAccount.owner_id == owner_id)
    account = q.first()
    if account is None:
        account = LedgerAccount(
            account_type=account_type,
            owner_id=owner_id,
            currency=currency,
        )
        db.add(account)
        db.flush()
    return account


def post_double_entry(
    db: Session,
    transaction_ref: str,
    debit_type: str,
    credit_type: str,
    amount: Decimal,
    debit_owner: uuid.UUID | None = None,
    credit_owner: uuid.UUID | None = None,
    description: str | None = None,
    currency: str = "USD",
) -> tuple[LedgerEntry, LedgerEntry]:
    """
    Post a balanced debit/credit pair.

    debit_type  — account type to debit  (e.g. "USER_WALLET")
    credit_type — account type to credit (e.g. "PAYMENT_PROCESSOR")
    """
    debit_account = _get_or_create_account(db, debit_type, debit_owner, currency)
    credit_account = _get_or_create_account(db, credit_type, credit_owner, currency)

    debit_entry = LedgerEntry(
        transaction_ref=transaction_ref,
        account_id=debit_account.id,
        debit=float(amount),
        credit=0,
        currency=currency,
        description=description,
    )
    credit_entry = LedgerEntry(
        transaction_ref=transaction_ref,
        account_id=credit_account.id,
        debit=0,
        credit=float(amount),
        currency=currency,
        description=description,
    )
    db.add(debit_entry)
    db.add(credit_entry)
    logger.debug(
        "Ledger: ref=%s debit=%s(%s) credit=%s(%s) amount=%s",
        transaction_ref, debit_type, debit_owner, credit_type, credit_owner, amount,
    )
    return debit_entry, credit_entry
