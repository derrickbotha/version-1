from __future__ import annotations


import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class Conversation(TimestampMixin, Base):
    __tablename__ = "conversations"

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

    # Relationships
    job: Mapped["Job"] = relationship("Job", foreign_keys=[job_id])  # noqa: F821
    student: Mapped["User"] = relationship(  # noqa: F821
        "User",
        foreign_keys=[student_id],
    )
    researcher: Mapped["User"] = relationship(  # noqa: F821
        "User",
        foreign_keys=[researcher_id],
    )
    messages: Mapped[list[Message]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Conversation id={self.id} job_id={self.job_id}>"


class Message(TimestampMixin, Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    message_type: Mapped[str] = mapped_column(
        Enum("text", "file", "system", name="message_type_enum"),
        nullable=False,
        default="text",
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    file_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    channel: Mapped[str] = mapped_column(
        Enum("platform", "whatsapp", name="message_channel_enum"),
        nullable=False,
        default="platform",
    )
    whatsapp_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    conversation: Mapped[Conversation] = relationship(
        "Conversation",
        back_populates="messages",
    )
    sender: Mapped["User"] = relationship("User", foreign_keys=[sender_id])  # noqa: F821

    def __repr__(self) -> str:
        return f"<Message id={self.id} type={self.message_type} channel={self.channel}>"


class Notification(TimestampMixin, Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notification_type: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])  # noqa: F821

    def __repr__(self) -> str:
        return f"<Notification id={self.id} user_id={self.user_id} read={self.read}>"
