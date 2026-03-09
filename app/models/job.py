from __future__ import annotations


import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class Job(TimestampMixin, Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    subject: Mapped[str] = mapped_column(String(150), nullable=False)
    academic_level: Mapped[str] = mapped_column(String(100), nullable=False)
    proposed_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
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
            name="job_status_enum",
        ),
        nullable=False,
        default="draft",
        index=True,
    )
    deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    student: Mapped["User"] = relationship(  # noqa: F821
        "User",
        foreign_keys=[student_id],
    )
    files: Mapped[list[JobFile]] = relationship(
        "JobFile",
        back_populates="job",
        cascade="all, delete-orphan",
    )
    bids: Mapped[list["Bid"]] = relationship(  # noqa: F821
        "Bid",
        back_populates="job",
        cascade="all, delete-orphan",
    )
    contract: Mapped["Contract | None"] = relationship(  # noqa: F821
        "Contract",
        back_populates="job",
        uselist=False,
    )

    def __repr__(self) -> str:
        return f"<Job id={self.id} title={self.title!r} status={self.status}>"


class JobFile(TimestampMixin, Base):
    __tablename__ = "job_files"

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
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Relationships
    job: Mapped[Job] = relationship("Job", back_populates="files")
    uploader: Mapped["User"] = relationship("User", foreign_keys=[uploaded_by])  # noqa: F821

    def __repr__(self) -> str:
        return f"<JobFile id={self.id} file_name={self.file_name!r}>"
