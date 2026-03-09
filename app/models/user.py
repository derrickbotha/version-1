from __future__ import annotations


import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class UserRole(str):
    STUDENT = "student"
    RESEARCHER = "researcher"
    PROFESSOR = "professor"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class UserStatus(str):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    phone: Mapped[str | None] = mapped_column(
        String(30),
        unique=True,
        nullable=True,
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(
        Enum("student", "researcher", "professor", "admin", "super_admin", name="user_role_enum"),
        nullable=False,
        default="student",
    )
    status: Mapped[str] = mapped_column(
        Enum("active", "suspended", "deleted", name="user_status_enum"),
        nullable=False,
        default="active",
    )
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    whatsapp_number: Mapped[str | None] = mapped_column(String(30), nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    student_profile: Mapped[StudentProfile | None] = relationship(
        "StudentProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    researcher_profile: Mapped[ResearcherProfile | None] = relationship(
        "ResearcherProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    wallet: Mapped["Wallet"] = relationship(  # noqa: F821 — forward ref
        "Wallet",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"


class StudentProfile(TimestampMixin, Base):
    __tablename__ = "student_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    university: Mapped[str | None] = mapped_column(String(255), nullable=True)
    degree_program: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="student_profile")

    def __repr__(self) -> str:
        return f"<StudentProfile user_id={self.user_id}>"


class ResearcherProfile(TimestampMixin, Base):
    __tablename__ = "researcher_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    expertise: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text),
        nullable=True,
        default=list,
    )
    rating: Mapped[float] = mapped_column(
        Numeric(3, 2),
        nullable=False,
        default=0,
    )
    total_jobs_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="researcher_profile")

    def __repr__(self) -> str:
        return f"<ResearcherProfile user_id={self.user_id} rating={self.rating}>"


# Avoid circular import: Wallet is defined in payment.py but we need it for User.wallet.
# The forward reference string "Wallet" in the relationship handles this at runtime.
from app.models.payment import Wallet  # noqa: E402, F401 — required for relationship resolution
