-- AI Resume Matching — database schema (PostgreSQL 16 + pgvector)
-- Embedding dimension must match EMBEDDING_DIM (default 1024, voyage-3).

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── Enums ───────────────────────────────────────────────────────────
CREATE TYPE user_role        AS ENUM ('admin', 'recruiter', 'hiring_manager', 'candidate');
CREATE TYPE doc_status       AS ENUM ('pending', 'processing', 'ready', 'failed');
CREATE TYPE match_status     AS ENUM ('pending', 'scored', 'failed');
CREATE TYPE review_status    AS ENUM ('unreviewed', 'approved', 'rejected', 'overridden');
CREATE TYPE confidence_level AS ENUM ('low', 'medium', 'high');
CREATE TYPE feedback_action  AS ENUM ('approve', 'reject', 'override', 'comment');

-- ── Users & auth ────────────────────────────────────────────────────
CREATE TABLE users (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name     TEXT NOT NULL,
    role          user_role NOT NULL DEFAULT 'candidate',
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── Resumes ─────────────────────────────────────────────────────────
-- parsed:        structured extraction (skills, experience, education...)
-- redacted_text: resume text AFTER PII/protected-attribute redaction.
--                Scoring and embeddings use ONLY this field.
CREATE TABLE resumes (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    file_key      TEXT,
    file_name     TEXT,
    mime_type     TEXT,
    raw_text      TEXT,
    redacted_text TEXT,
    parsed        JSONB,
    status        doc_status NOT NULL DEFAULT 'pending',
    error         TEXT,
    embedding     vector(1024),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX resumes_owner_idx ON resumes(owner_id);
CREATE INDEX resumes_embedding_idx ON resumes
    USING hnsw (embedding vector_cosine_ops);

-- Chunk-level embeddings for finer-grained semantic search
CREATE TABLE resume_chunks (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    resume_id   UUID NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    content     TEXT NOT NULL,
    embedding   vector(1024)
);
CREATE INDEX resume_chunks_resume_idx ON resume_chunks(resume_id);
CREATE INDEX resume_chunks_embedding_idx ON resume_chunks
    USING hnsw (embedding vector_cosine_ops);

-- ── Job descriptions ───────────────────────────────────────────────
CREATE TABLE jobs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_by      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title           TEXT NOT NULL,
    company         TEXT,
    location        TEXT,
    employment_type TEXT,
    description_raw TEXT NOT NULL,
    file_key        TEXT,
    parsed          JSONB,
    status          doc_status NOT NULL DEFAULT 'pending',
    error           TEXT,
    is_open         BOOLEAN NOT NULL DEFAULT TRUE,
    embedding       vector(1024),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX jobs_created_by_idx ON jobs(created_by);
CREATE INDEX jobs_embedding_idx ON jobs
    USING hnsw (embedding vector_cosine_ops);

-- ── Matches ────────────────────────────────────────────────────────
CREATE TABLE matches (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    resume_id        UUID NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
    job_id           UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    status           match_status NOT NULL DEFAULT 'pending',
    overall_score    NUMERIC(5,2),            -- 0..100
    confidence       confidence_level,
    semantic_score   NUMERIC(5,2),
    skills_score     NUMERIC(5,2),
    experience_score NUMERIC(5,2),
    education_score  NUMERIC(5,2),
    matched_skills   JSONB,
    missing_skills   JSONB,
    gaps             JSONB,                    -- experience/education/cert gaps + role-fit concerns
    explanation      JSONB,                    -- evidence-based reasoning from LLM
    model_version    TEXT,
    review_status    review_status NOT NULL DEFAULT 'unreviewed',
    reviewed_by      UUID REFERENCES users(id),
    override_score   NUMERIC(5,2),
    error            TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (resume_id, job_id)
);
CREATE INDEX matches_job_idx    ON matches(job_id, overall_score DESC);
CREATE INDEX matches_resume_idx ON matches(resume_id, overall_score DESC);

-- ── Feedback (human review → training signal) ─────────────────────
CREATE TABLE feedback (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    match_id          UUID NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    user_id           UUID NOT NULL REFERENCES users(id),
    action            feedback_action NOT NULL,
    label_score       INT CHECK (label_score BETWEEN 0 AND 100),
    comment           TEXT,
    privacy_checked   BOOLEAN NOT NULL DEFAULT FALSE,
    used_for_training BOOLEAN NOT NULL DEFAULT FALSE,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX feedback_match_idx ON feedback(match_id);

-- ── Audit trail (every AI decision is logged) ─────────────────────
CREATE TABLE audit_logs (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    actor_id    UUID REFERENCES users(id),
    event_type  TEXT NOT NULL,        -- e.g. match.scored, resume.parsed, feedback.recorded
    entity_type TEXT NOT NULL,
    entity_id   UUID,
    model_version TEXT,
    input_hash  TEXT,                 -- sha256 of redacted inputs, for reproducibility
    details     JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX audit_logs_entity_idx ON audit_logs(entity_type, entity_id);
CREATE INDEX audit_logs_created_idx ON audit_logs(created_at DESC);

-- ── Evaluation & training runs ─────────────────────────────────────
CREATE TABLE eval_runs (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_version TEXT NOT NULL,
    dataset_size  INT NOT NULL,
    metrics       JSONB NOT NULL,     -- mae, agreement_rate, precision_at_5 ...
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE training_runs (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    base_model   TEXT NOT NULL,
    dataset_size INT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'exported',  -- exported | queued | running | done | failed
    artifacts    JSONB,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
