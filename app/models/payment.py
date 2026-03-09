from __future__ import annotations


import uuid

from sqlalchemy import Boolean, CheckConstraint, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class Payment(TimestampMixin, Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    contract_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contracts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    researcher_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum(
            "pending",
            "escrowed",
            "released",
            "refunded",
            "failed",
            name="payment_status_enum",
        ),
        nullable=False,
        default="pending",
        index=True,
    )
    payment_provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    provider_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    contract: Mapped["Contract"] = relationship(  # noqa: F821
        "Contract",
        back_populates="payments",
    )
    student: Mapped["User"] = relationship(  # noqa: F821
        "User",
        foreign_keys=[student_id],
    )
    researcher: Mapped["User"] = relationship(  # noqa: F821
        "User",
        foreign_keys=[researcher_id],
    )

    def __repr__(self) -> str:
        return f"<Payment id={self.id} amount={self.amount} status={self.status}>"


class Wallet(TimestampMixin, Base):
    __tablename__ = "wallets"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    balance: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="wallet")  # noqa: F821
    transactions: Mapped[list[WalletTransaction]] = relationship(
        "WalletTransaction",
        back_populates="wallet",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Wallet user_id={self.user_id} balance={self.balance}>"


class WalletTransaction(TimestampMixin, Base):
    __tablename__ = "wallet_transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    wallet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("wallets.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    transaction_type: Mapped[str] = mapped_column(
        Enum(
            "deposit",
            "escrow_lock",
            "release",
            "refund",
            "payout",
            name="wallet_transaction_type_enum",
        ),
        nullable=False,
        index=True,
    )
    reference_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    wallet: Mapped[Wallet] = relationship("Wallet", back_populates="transactions")

    def __repr__(self) -> str:
        return (
            f"<WalletTransaction id={self.id} type={self.transaction_type} amount={self.amount}>"
        )


# ---------------------------------------------------------------------------
# Ledger — double-entry accounting (spec §4.4, §4.5, §6)
# ---------------------------------------------------------------------------

import datetime as _dt
from sqlalchemy import DateTime as _DateTime


class LedgerAccount(Base):
    """A named account in the double-entry ledger (spec §4.4)."""
    __tablename__ = "ledger_accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_type: Mapped[str] = mapped_column(
        Enum(
            "USER_WALLET", "WRITER_WALLET", "ESCROW_ACCOUNT", "PLATFORM_REVENUE",
            "PAYMENT_PROCESSOR", "REFUND_POOL", "PAYOUT_CLEARING",
            name="ledger_account_type_enum",
        ),
        nullable=False,
        index=True,
    )
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    created_at: Mapped[_dt.datetime] = mapped_column(
        _DateTime(timezone=True),
        nullable=False,
        default=lambda: _dt.datetime.now(_dt.timezone.utc),
    )

    entries: Mapped[list["LedgerEntry"]] = relationship("LedgerEntry", back_populates="account")

    def __repr__(self) -> str:
        return f"<LedgerAccount type={self.account_type} owner={self.owner_id}>"


class LedgerEntry(Base):
    """Single debit or credit line in the double-entry ledger (spec §4.5)."""
    __tablename__ = "ledger_entries"
    __table_args__ = (
        CheckConstraint("debit >= 0", name="ck_ledger_debit_positive"),
        CheckConstraint("credit >= 0", name="ck_ledger_credit_positive"),
        CheckConstraint("NOT (debit > 0 AND credit > 0)", name="ck_ledger_one_side_only"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_ref: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ledger_accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    debit: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    credit: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[_dt.datetime] = mapped_column(
        _DateTime(timezone=True),
        nullable=False,
        default=lambda: _dt.datetime.now(_dt.timezone.utc),
    )

    account: Mapped[LedgerAccount] = relationship("LedgerAccount", back_populates="entries")

    def __repr__(self) -> str:
        return f"<LedgerEntry ref={self.transaction_ref} debit={self.debit} credit={self.credit}>"


# ---------------------------------------------------------------------------
# PaymentMethod — saved cards / PayPal (spec §4.7)
# ---------------------------------------------------------------------------

class PaymentMethod(TimestampMixin, Base):
    """Saved payment method (card token or PayPal) for a user (spec §4.7)."""
    __tablename__ = "payment_methods"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(
        Enum("stripe", "paypal", name="payment_method_provider_enum"),
        nullable=False,
    )
    provider_token: Mapped[str] = mapped_column(Text, nullable=False)  # Stripe PM id or PayPal billing agreement
    brand: Mapped[str | None] = mapped_column(String(50), nullable=True)   # visa, mastercard, paypal
    last4: Mapped[str | None] = mapped_column(String(4), nullable=True)
    expiry_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expiry_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    def __repr__(self) -> str:
        return f"<PaymentMethod id={self.id} provider={self.provider} last4={self.last4}>"


# ---------------------------------------------------------------------------
# WriterPayout — tracks payouts to researchers (spec §4.10)
# ---------------------------------------------------------------------------

class WriterPayout(TimestampMixin, Base):
    """Payout request for a researcher/writer (spec §4.10)."""
    __tablename__ = "writer_payouts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    writer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    status: Mapped[str] = mapped_column(
        Enum("pending", "processing", "completed", "failed", name="writer_payout_status_enum"),
        nullable=False,
        default="pending",
        index=True,
    )
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    provider_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    writer: Mapped["User"] = relationship("User", foreign_keys=[writer_id])  # noqa: F821

    def __repr__(self) -> str:
        return f"<WriterPayout id={self.id} writer={self.writer_id} amount={self.amount} status={self.status}>"


# ---------------------------------------------------------------------------
# IdempotencyKey — prevents duplicate payment operations (spec §12)
# ---------------------------------------------------------------------------

class IdempotencyKey(Base):
    """Stores processed idempotency keys to prevent duplicate operations (spec §12)."""
    __tablename__ = "idempotency_keys"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False)
    response_body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[_dt.datetime] = mapped_column(
        _DateTime(timezone=True),
        nullable=False,
        default=lambda: _dt.datetime.now(_dt.timezone.utc),
    )
