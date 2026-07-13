import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

EMBED_DIM = 1024

# Portable column types: native JSONB/vector on Postgres, plain JSON on
# SQLite (dev mode). Cosine math happens in Python either way for matches;
# only pgvector's HNSW index is Postgres-specific.
JSONCol = JSON().with_variant(JSONB(), "postgresql")
EmbeddingCol = JSON().with_variant(Vector(EMBED_DIM), "postgresql")
UUID = Uuid  # generic UUID type works on both dialects

user_role = Enum("admin", "recruiter", "hiring_manager", "candidate", name="user_role")
doc_status = Enum("pending", "processing", "ready", "failed", name="doc_status")
match_status = Enum("pending", "scored", "failed", name="match_status")
review_status = Enum("unreviewed", "approved", "rejected", "overridden", name="review_status")
confidence_level = Enum("low", "medium", "high", name="confidence_level")
feedback_action = Enum("approve", "reject", "override", "comment", name="feedback_action")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(Text, unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    full_name: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(user_role, default="candidate")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    file_key: Mapped[str | None] = mapped_column(Text)
    file_name: Mapped[str | None] = mapped_column(Text)
    mime_type: Mapped[str | None] = mapped_column(Text)
    raw_text: Mapped[str | None] = mapped_column(Text)
    redacted_text: Mapped[str | None] = mapped_column(Text)
    parsed: Mapped[dict | None] = mapped_column(JSONCol)
    status: Mapped[str] = mapped_column(doc_status, default="pending")
    error: Mapped[str | None] = mapped_column(Text)
    embedding: Mapped[list | None] = mapped_column(EmbeddingCol)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    owner: Mapped[User] = relationship()


class ResumeChunk(Base):
    __tablename__ = "resume_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resume_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resumes.id", ondelete="CASCADE"))
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list | None] = mapped_column(EmbeddingCol)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(Text)
    company: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(Text)
    employment_type: Mapped[str | None] = mapped_column(Text)
    description_raw: Mapped[str] = mapped_column(Text)
    file_key: Mapped[str | None] = mapped_column(Text)
    parsed: Mapped[dict | None] = mapped_column(JSONCol)
    status: Mapped[str] = mapped_column(doc_status, default="pending")
    error: Mapped[str | None] = mapped_column(Text)
    is_open: Mapped[bool] = mapped_column(Boolean, default=True)
    embedding: Mapped[list | None] = mapped_column(EmbeddingCol)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (UniqueConstraint("resume_id", "job_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resume_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resumes.id", ondelete="CASCADE"))
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(match_status, default="pending")
    overall_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    confidence: Mapped[str | None] = mapped_column(confidence_level)
    semantic_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    skills_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    experience_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    education_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    matched_skills: Mapped[list | None] = mapped_column(JSONCol)
    missing_skills: Mapped[list | None] = mapped_column(JSONCol)
    gaps: Mapped[dict | None] = mapped_column(JSONCol)
    explanation: Mapped[dict | None] = mapped_column(JSONCol)
    model_version: Mapped[str | None] = mapped_column(Text)
    review_status: Mapped[str] = mapped_column(review_status, default="unreviewed")
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    override_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    resume: Mapped[Resume] = relationship()
    job: Mapped[Job] = relationship()


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    match_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(feedback_action)
    label_score: Mapped[int | None] = mapped_column(Integer)
    comment: Mapped[str | None] = mapped_column(Text)
    privacy_checked: Mapped[bool] = mapped_column(Boolean, default=False)
    used_for_training: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    event_type: Mapped[str] = mapped_column(Text)
    entity_type: Mapped[str] = mapped_column(Text)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    model_version: Mapped[str | None] = mapped_column(Text)
    input_hash: Mapped[str | None] = mapped_column(Text)
    details: Mapped[dict | None] = mapped_column(JSONCol)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EvalRun(Base):
    __tablename__ = "eval_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_version: Mapped[str] = mapped_column(Text)
    dataset_size: Mapped[int] = mapped_column(Integer)
    metrics: Mapped[dict] = mapped_column(JSONCol)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TrainingRun(Base):
    __tablename__ = "training_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    base_model: Mapped[str] = mapped_column(Text)
    dataset_size: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(Text, default="exported")
    artifacts: Mapped[dict | None] = mapped_column(JSONCol)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
