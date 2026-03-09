"""
Professor, Institution, and academic review models.

Role hierarchy: super_admin > admin > professor > researcher > student

A Professor:
  - Has an institutional affiliation (verified by admin)
  - Reviews submitted research work against rubrics (QualityReview)
  - Verifies researcher credentials (ResearcherCredential)
  - Issues endorsements that boost researcher credibility
  - Creates CourseAssignment templates that students post as jobs
  - Serves as academic arbiter in disputes (DisputeRuling)
  - Gets paid a platform fee per completed review
"""

from __future__ import annotations

import uuid
import datetime as _dt

from sqlalchemy import (
    Boolean,
    CheckConstraint,
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


# ─────────────────────────────────────────────────────────────────────────────
# Institution
# ─────────────────────────────────────────────────────────────────────────────

class Institution(TimestampMixin, Base):
    """
    Verified academic institution.  Admin must approve before a professor
    can associate themselves with it.
    """
    __tablename__ = "institutions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    domain: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="e.g. 'mit.edu' for email verification"
    )
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verified_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    professors: Mapped[list[ProfessorProfile]] = relationship(
        "ProfessorProfile", back_populates="institution"
    )

    def __repr__(self) -> str:
        return f"<Institution name={self.name} verified={self.is_verified}>"


# ─────────────────────────────────────────────────────────────────────────────
# ProfessorProfile
# ─────────────────────────────────────────────────────────────────────────────

class ProfessorProfile(TimestampMixin, Base):
    """
    Extended profile for users with role='professor'.

    Approval workflow:
      pending → approved (by admin) → active
      pending → rejected (by admin)
      approved → suspended (by admin)

    A professor only gets review queue items + payout once status='approved'.
    """
    __tablename__ = "professor_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    institution_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="e.g. 'Dr.', 'Prof.', 'Associate Prof.'"
    )
    department: Mapped[str | None] = mapped_column(String(200), nullable=True)
    academic_rank: Mapped[str | None] = mapped_column(
        Enum(
            "lecturer", "assistant_professor", "associate_professor",
            "full_professor", "emeritus", "adjunct",
            name="academic_rank_enum",
        ),
        nullable=True,
    )
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    expertise_areas: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text), nullable=True, default=list
    )
    orcid_id: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="ORCID researcher identifier"
    )
    linkedin_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    institutional_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("pending", "approved", "rejected", "suspended", name="professor_status_enum"),
        nullable=False,
        default="pending",
        index=True,
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[_dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Subjects this professor is qualified to review
    review_subjects: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text), nullable=True, default=list
    )
    # Stats
    total_reviews_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_review_score_given: Mapped[float] = mapped_column(
        Numeric(4, 2), nullable=False, default=0
    )
    review_fee_per_job: Mapped[float] = mapped_column(
        Numeric(8, 2), nullable=False, default=5.00,
        comment="USD platform fee paid to professor per review"
    )

    # Relationships
    user: Mapped["User"] = relationship(  # noqa: F821
        "User", foreign_keys=[user_id], backref="professor_profile"
    )
    institution: Mapped[Institution | None] = relationship(
        "Institution", back_populates="professors"
    )
    credentials_verified: Mapped[list[ResearcherCredential]] = relationship(
        "ResearcherCredential", back_populates="verified_by_professor",
        foreign_keys="ResearcherCredential.verified_by_id",
    )
    endorsements_given: Mapped[list[ProfessorEndorsement]] = relationship(
        "ProfessorEndorsement", back_populates="professor"
    )
    quality_reviews: Mapped[list[QualityReview]] = relationship(
        "QualityReview", back_populates="professor"
    )
    dispute_rulings: Mapped[list[DisputeRuling]] = relationship(
        "DisputeRuling", back_populates="professor"
    )
    assignments: Mapped[list[CourseAssignment]] = relationship(
        "CourseAssignment", back_populates="professor"
    )

    def __repr__(self) -> str:
        return f"<ProfessorProfile user_id={self.user_id} status={self.status}>"


# ─────────────────────────────────────────────────────────────────────────────
# ResearcherCredential
# ─────────────────────────────────────────────────────────────────────────────

class ResearcherCredential(TimestampMixin, Base):
    """
    Academic credential for a researcher, verified by a professor.

    A researcher submits their credential (degree, certification, publication).
    A professor reviews and marks it verified or rejected.
    Verified credentials appear on researcher's public profile, boosting bid
    credibility and unlocking premium job categories.
    """
    __tablename__ = "researcher_credentials"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    researcher_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    credential_type: Mapped[str] = mapped_column(
        Enum(
            "bachelors_degree", "masters_degree", "phd", "postdoc",
            "professional_certification", "publication", "award", "other",
            name="credential_type_enum",
        ),
        nullable=False,
    )
    institution_name: Mapped[str] = mapped_column(String(255), nullable=False)
    field_of_study: Mapped[str | None] = mapped_column(String(255), nullable=True)
    year_obtained: Mapped[int | None] = mapped_column(Integer, nullable=True)
    document_url: Mapped[str | None] = mapped_column(
        String(1000), nullable=True, comment="S3 URL to scanned credential"
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("pending", "verified", "rejected", name="credential_status_enum"),
        nullable=False,
        default="pending",
        index=True,
    )
    verified_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("professor_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    verified_at: Mapped[_dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    researcher: Mapped["User"] = relationship(  # noqa: F821
        "User", foreign_keys=[researcher_id]
    )
    verified_by_professor: Mapped[ProfessorProfile | None] = relationship(
        "ProfessorProfile",
        foreign_keys=[verified_by_id],
        back_populates="credentials_verified",
    )

    def __repr__(self) -> str:
        return (
            f"<ResearcherCredential researcher={self.researcher_id} "
            f"type={self.credential_type} status={self.status}>"
        )


# ─────────────────────────────────────────────────────────────────────────────
# ProfessorEndorsement
# ─────────────────────────────────────────────────────────────────────────────

class ProfessorEndorsement(TimestampMixin, Base):
    """
    A professor publicly endorses a researcher for a specific area of expertise.
    Endorsements are visible on the researcher's profile and boost search ranking.
    One professor can endorse the same researcher only once per subject area.
    """
    __tablename__ = "professor_endorsements"
    __table_args__ = (
        UniqueConstraint(
            "professor_id", "researcher_id", "subject_area",
            name="uq_endorsement_professor_researcher_subject"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    professor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("professor_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    researcher_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject_area: Mapped[str] = mapped_column(String(200), nullable=False)
    endorsement_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    professor: Mapped[ProfessorProfile] = relationship(
        "ProfessorProfile", back_populates="endorsements_given"
    )
    researcher: Mapped["User"] = relationship(  # noqa: F821
        "User", foreign_keys=[researcher_id]
    )

    def __repr__(self) -> str:
        return (
            f"<Endorsement professor={self.professor_id} "
            f"researcher={self.researcher_id} area={self.subject_area}>"
        )


# ─────────────────────────────────────────────────────────────────────────────
# CourseAssignment
# ─────────────────────────────────────────────────────────────────────────────

class CourseAssignment(TimestampMixin, Base):
    """
    A professor creates an assignment template. Students who are linked to the
    professor's course can use this template to quickly post a job. The professor
    can optionally set a grading rubric and quality threshold.

    Template fields pre-populate the job creation form.
    """
    __tablename__ = "course_assignments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    professor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("professor_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    academic_level: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Rubric as free-form text (markdown) — future: JSON rubric schema
    rubric: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Minimum quality score (0–100) a submission must achieve for auto-approval
    min_quality_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Whether professor review is mandatory before payment release
    review_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    suggested_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    deadline_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    professor: Mapped[ProfessorProfile] = relationship(
        "ProfessorProfile", back_populates="assignments"
    )
    reviews: Mapped[list[QualityReview]] = relationship(
        "QualityReview",
        primaryjoin="QualityReview.assignment_id == CourseAssignment.id",
        back_populates="assignment",
    )

    def __repr__(self) -> str:
        return f"<CourseAssignment title={self.title!r} professor={self.professor_id}>"


# ─────────────────────────────────────────────────────────────────────────────
# QualityReview
# ─────────────────────────────────────────────────────────────────────────────

class QualityReview(TimestampMixin, Base):
    """
    Professor's formal review of a submitted contract.

    Lifecycle:
      pending → in_review → approved | revision_required | rejected

    - score: 0–100 (maps to letter grade)
    - originality_score: 0–100 (plagiarism check result)
    - If review_required on the assignment, payment is HELD until 'approved'
    - If 'rejected', student gets a full refund; researcher is penalised
    - Multiple review rounds allowed (revision_required → researcher resubmits)
    """
    __tablename__ = "quality_reviews"
    __table_args__ = (
        CheckConstraint("score >= 0 AND score <= 100", name="ck_qr_score_range"),
        CheckConstraint(
            "originality_score >= 0 AND originality_score <= 100",
            name="ck_qr_originality_range",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    contract_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contracts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    professor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("professor_profiles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    assignment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("course_assignments.id", ondelete="SET NULL"),
        nullable=True,
    )
    submission_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("submissions.id", ondelete="SET NULL"),
        nullable=True,
    )
    round_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(
        Enum(
            "pending", "in_review", "approved", "revision_required", "rejected",
            name="quality_review_status_enum",
        ),
        nullable=False,
        default="pending",
        index=True,
    )
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    originality_score: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Plagiarism score 0-100 (100=original)"
    )
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    rubric_scores: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="JSON: {criterion: score} breakdown"
    )
    payment_held: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="True when payment release is gated on this review"
    )
    reviewed_at: Mapped[_dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Professor fee earned for this review
    fee_amount: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    fee_paid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    contract: Mapped["Contract"] = relationship(  # noqa: F821
        "Contract", foreign_keys=[contract_id]
    )
    professor: Mapped[ProfessorProfile] = relationship(
        "ProfessorProfile", back_populates="quality_reviews"
    )
    assignment: Mapped[CourseAssignment | None] = relationship(
        "CourseAssignment", back_populates="reviews"
    )

    def __repr__(self) -> str:
        return (
            f"<QualityReview contract={self.contract_id} "
            f"status={self.status} score={self.score}>"
        )


# ─────────────────────────────────────────────────────────────────────────────
# DisputeRuling
# ─────────────────────────────────────────────────────────────────────────────

class DisputeRuling(TimestampMixin, Base):
    """
    A professor's academic ruling on a contract dispute.

    When admin assigns a professor to a dispute, the professor reviews all
    materials (job spec, submission, messages) and issues a ruling that
    recommends one of:
      - full_release: pay researcher in full
      - partial_release: release a percentage to researcher
      - full_refund: refund student entirely
      - revision: require another revision round

    The admin then executes the financial outcome.  The professor's ruling
    is binding unless overridden by super_admin.
    """
    __tablename__ = "dispute_rulings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    dispute_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("disputes.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    professor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("professor_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    ruling: Mapped[str] = mapped_column(
        Enum(
            "full_release", "partial_release", "full_refund", "revision",
            name="dispute_ruling_enum",
        ),
        nullable=False,
    )
    release_percentage: Mapped[float | None] = mapped_column(
        Numeric(5, 2), nullable=True,
        comment="For partial_release: % of escrow to release to researcher"
    )
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_reviewed: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Summary of materials reviewed (files, messages, rubric)"
    )
    submitted_at: Mapped[_dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    overridden_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
        comment="super_admin who overrode this ruling"
    )
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    professor: Mapped[ProfessorProfile] = relationship(
        "ProfessorProfile", back_populates="dispute_rulings"
    )

    def __repr__(self) -> str:
        return (
            f"<DisputeRuling dispute={self.dispute_id} "
            f"ruling={self.ruling} professor={self.professor_id}>"
        )


# ─────────────────────────────────────────────────────────────────────────────
# ReviewQueueItem
# ─────────────────────────────────────────────────────────────────────────────

class ReviewQueueItem(TimestampMixin, Base):
    """
    Work item in the professor review queue.

    When a contract's submission is ready for review, a queue item is
    created and assigned to the best-matched available professor
    (matched on review_subjects vs job subject, then by workload).

    SLA: professor must action within `sla_hours` or item is reassigned.
    """
    __tablename__ = "review_queue"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    contract_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contracts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    professor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("professor_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    queue_type: Mapped[str] = mapped_column(
        Enum("quality_review", "credential_verification", "dispute_arbitration",
             name="queue_type_enum"),
        nullable=False,
        default="quality_review",
    )
    status: Mapped[str] = mapped_column(
        Enum("queued", "assigned", "in_progress", "completed", "reassigned", "expired",
             name="queue_status_enum"),
        nullable=False,
        default="queued",
        index=True,
    )
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5,
        comment="1=urgent, 10=low. Disputes always priority 1."
    )
    sla_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=48)
    due_at: Mapped[_dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    assigned_at: Mapped[_dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[_dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<ReviewQueueItem contract={self.contract_id} "
            f"type={self.queue_type} status={self.status}>"
        )


# ─────────────────────────────────────────────────────────────────────────────
# PlatformConfig
# ─────────────────────────────────────────────────────────────────────────────

class PlatformConfig(Base):
    """
    Admin-editable key/value platform configuration store.
    Values are stored as strings and cast at runtime.

    Examples:
      platform_fee_pct         = "15"      # % taken from every released payment
      professor_review_fee_usd = "5.00"    # base fee per review
      max_revision_rounds      = "3"
      quality_review_required  = "false"   # global default
      dispute_sla_hours        = "72"
      payout_min_usd           = "10"
    """
    __tablename__ = "platform_config"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[_dt.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: _dt.datetime.now(_dt.timezone.utc),
        onupdate=lambda: _dt.datetime.now(_dt.timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<PlatformConfig {self.key}={self.value}>"
