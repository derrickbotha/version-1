from __future__ import annotations


import uuid

from sqlalchemy import Enum, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class Bid(TimestampMixin, Base):
    __tablename__ = "bids"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    researcher_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    proposed_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum(
            "pending",
            "accepted",
            "rejected",
            "countered",
            "withdrawn",
            name="bid_status_enum",
        ),
        nullable=False,
        default="pending",
        index=True,
    )

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="bids")  # noqa: F821
    researcher: Mapped["User"] = relationship(  # noqa: F821
        "User",
        foreign_keys=[researcher_id],
    )
    counters: Mapped[list[BidCounter]] = relationship(
        "BidCounter",
        back_populates="bid",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Bid id={self.id} job_id={self.job_id} status={self.status}>"


class BidCounter(TimestampMixin, Base):
    __tablename__ = "bid_counters"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    bid_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bids.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    counter_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    new_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    bid: Mapped[Bid] = relationship("Bid", back_populates="counters")
    counter_user: Mapped["User"] = relationship(  # noqa: F821
        "User",
        foreign_keys=[counter_by],
    )

    def __repr__(self) -> str:
        return f"<BidCounter id={self.id} bid_id={self.bid_id} new_price={self.new_price}>"
