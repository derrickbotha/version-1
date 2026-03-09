from __future__ import annotations


import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class Contract(TimestampMixin, Base):
    __tablename__ = "contracts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="RESTRICT"),
        unique=True,
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
    agreed_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    start_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        Enum(
            "draft",
            "open",
            "negotiation",
            "accepted",
            "in_progress",
            "submitted",
            "revision_requested",
            "completed",
            "cancelled",
            "disputed",
            name="contract_status_enum",
        ),
        nullable=False,
        default="accepted",
        index=True,
    )

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="contract")  # noqa: F821
    student: Mapped["User"] = relationship(  # noqa: F821
        "User",
        foreign_keys=[student_id],
    )
    researcher: Mapped["User"] = relationship(  # noqa: F821
        "User",
        foreign_keys=[researcher_id],
    )
    rating: Mapped[Rating | None] = relationship(
        "Rating",
        back_populates="contract",
        uselist=False,
        cascade="all, delete-orphan",
    )
    dispute: Mapped[Dispute | None] = relationship(
        "Dispute",
        back_populates="contract",
        uselist=False,
        cascade="all, delete-orphan",
    )
    payments: Mapped[list["Payment"]] = relationship(  # noqa: F821
        "Payment",
        back_populates="contract",
    )
    submissions: Mapped[list["Submission"]] = relationship(  # noqa: F821
        "Submission",
        back_populates="contract",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Contract id={self.id} status={self.status}>"


class Rating(TimestampMixin, Base):
    __tablename__ = "ratings"
    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_rating_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    contract_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contracts.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    researcher_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    review: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    contract: Mapped[Contract] = relationship("Contract", back_populates="rating")
    student: Mapped["User"] = relationship(  # noqa: F821
        "User",
        foreign_keys=[student_id],
    )
    researcher: Mapped["User"] = relationship(  # noqa: F821
        "User",
        foreign_keys=[researcher_id],
    )

    def __repr__(self) -> str:
        return f"<Rating id={self.id} rating={self.rating}>"


class Dispute(TimestampMixin, Base):
    __tablename__ = "disputes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    contract_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contracts.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    opened_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum(
            "open",
            "investigating",
            "resolved",
            "closed",
            name="dispute_status_enum",
        ),
        nullable=False,
        default="open",
        index=True,
    )
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    contract: Mapped[Contract] = relationship("Contract", back_populates="dispute")
    opener: Mapped["User"] = relationship(  # noqa: F821
        "User",
        foreign_keys=[opened_by],
    )
    resolver: Mapped["User | None"] = relationship(  # noqa: F821
        "User",
        foreign_keys=[resolved_by],
    )

    def __repr__(self) -> str:
        return f"<Dispute id={self.id} status={self.status}>"


# Resolve forward references needed by Contract
from app.models.payment import Payment  # noqa: E402, F401
from app.models.submission import Submission  # noqa: E402, F401
