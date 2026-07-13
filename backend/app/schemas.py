import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

Role = Literal["admin", "recruiter", "hiring_manager", "candidate"]


# ── Auth ────────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str
    role: Role = "candidate"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Role
    user_id: uuid.UUID
    full_name: str


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: Role
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Structured extraction (LLM output schemas) ─────────────────────
class WorkExperience(BaseModel):
    title: str
    company: str | None = None
    start_year: int | None = None
    end_year: int | None = None  # None = present
    highlights: list[str] = []


class Education(BaseModel):
    degree: str
    field: str | None = None
    institution: str | None = None
    year: int | None = None


class ParsedResume(BaseModel):
    """Job-relevant fields only. Never includes name, contact info, photo,
    date of birth, or any protected attribute."""

    summary: str = ""
    skills: list[str] = []
    total_years_experience: float | None = None
    work_experience: list[WorkExperience] = []
    education: list[Education] = []
    certifications: list[str] = []
    languages_spoken: list[str] = []


class ParsedJob(BaseModel):
    title: str = ""
    summary: str = ""
    required_skills: list[str] = []
    preferred_skills: list[str] = []
    min_years_experience: float | None = None
    education_required: str | None = None
    certifications_required: list[str] = []
    responsibilities: list[str] = []
    seniority: str | None = None


class MatchExplanation(BaseModel):
    """Evidence-based reasoning. Must reference only job-relevant evidence."""

    strengths: list[str] = []
    concerns: list[str] = []
    experience_gaps: list[str] = []
    education_certification_gaps: list[str] = []
    role_fit_summary: str = ""
    recommendation_note: str = (
        "Decision support only — a human reviewer must make the final decision."
    )


# ── API resources ───────────────────────────────────────────────────
class ResumeOut(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    file_name: str | None
    status: str
    parsed: dict | None
    error: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class JobCreate(BaseModel):
    title: str
    company: str | None = None
    location: str | None = None
    employment_type: str | None = None
    description: str


class JobOut(BaseModel):
    id: uuid.UUID
    created_by: uuid.UUID
    title: str
    company: str | None
    location: str | None
    employment_type: str | None
    description_raw: str
    status: str
    parsed: dict | None
    is_open: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class MatchRequest(BaseModel):
    resume_id: uuid.UUID
    job_id: uuid.UUID


class BatchMatchRequest(BaseModel):
    job_id: uuid.UUID | None = None      # one JD → many resumes
    resume_id: uuid.UUID | None = None   # one resume → many JDs
    limit: int = Field(default=25, le=100)


class MatchOut(BaseModel):
    id: uuid.UUID
    resume_id: uuid.UUID
    job_id: uuid.UUID
    status: str
    overall_score: float | None
    confidence: str | None
    semantic_score: float | None
    skills_score: float | None
    experience_score: float | None
    education_score: float | None
    matched_skills: list | None
    missing_skills: list | None
    gaps: dict | None
    explanation: dict | None
    model_version: str | None
    review_status: str
    override_score: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RankedMatchOut(MatchOut):
    job_title: str | None = None
    resume_file_name: str | None = None


class FeedbackCreate(BaseModel):
    match_id: uuid.UUID
    action: Literal["approve", "reject", "override", "comment"]
    label_score: int | None = Field(default=None, ge=0, le=100)
    comment: str | None = None


class FeedbackOut(BaseModel):
    id: uuid.UUID
    match_id: uuid.UUID
    action: str
    label_score: int | None
    comment: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogOut(BaseModel):
    id: uuid.UUID
    event_type: str
    entity_type: str
    entity_id: uuid.UUID | None
    model_version: str | None
    input_hash: str | None
    details: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


class EvalRunOut(BaseModel):
    id: uuid.UUID
    model_version: str
    dataset_size: int
    metrics: dict
    created_at: datetime

    model_config = {"from_attributes": True}
