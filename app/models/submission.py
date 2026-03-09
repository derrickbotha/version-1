from __future__ import annotations


import uuid

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class Submission(TimestampMixin, Base):
    __tablename__ = "submissions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    contract_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contracts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    researcher_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    submission_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum(
            "submitted",
            "approved",
            "revision_requested",
            name="submission_status_enum",
        ),
        nullable=False,
        default="submitted",
        index=True,
    )

    # Relationships
    contract: Mapped["Contract"] = relationship(  # noqa: F821
        "Contract",
        back_populates="submissions",
    )
    researcher: Mapped["User"] = relationship(  # noqa: F821
        "User",
        foreign_keys=[researcher_id],
    )
    files: Mapped[list[SubmissionFile]] = relationship(
        "SubmissionFile",
        back_populates="submission",
        cascade="all, delete-orphan",
    )
    revisions: Mapped[list[Revision]] = relationship(
        "Revision",
        back_populates="submission",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Submission id={self.id} status={self.status}>"


class SubmissionFile(TimestampMixin, Base):
    __tablename__ = "submission_files"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    submission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("submissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    submission: Mapped[Submission] = relationship("Submission", back_populates="files")

    def __repr__(self) -> str:
        return f"<SubmissionFile id={self.id} file_name={self.file_name!r}>"


class Revision(TimestampMixin, Base):
    __tablename__ = "revisions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    submission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("submissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requested_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    submission: Mapped[Submission] = relationship("Submission", back_populates="revisions")
    requester: Mapped["User"] = relationship(  # noqa: F821
        "User",
        foreign_keys=[requested_by],
    )

    def __repr__(self) -> str:
        return f"<Revision id={self.id} submission_id={self.submission_id}>"
