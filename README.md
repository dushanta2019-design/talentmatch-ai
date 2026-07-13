# TalentMatch AI — Resume ⇄ Job Matching Platform

Production-ready, compliance-first AI resume matching: upload resumes and job
descriptions, get explainable 0–100 match scores, rank candidates per job or
jobs per candidate, and keep humans in control of every decision.

**The AI never makes hiring decisions.** It produces evidence-based decision
support; recruiters approve, reject, or override every match. See
[docs/COMPLIANCE.md](docs/COMPLIANCE.md).

## Architecture

```
frontend/        Next.js 14 + TypeScript + Tailwind (recruiter / candidate / admin dashboards)
backend/         FastAPI + SQLAlchemy (async) — REST API, auth (JWT, RBAC), AI services
  app/services/  PII redaction · Claude parsing & explanations · embeddings · hybrid scorer
  app/workers/   arq background jobs (parse, embed, score)
db/              PostgreSQL 16 + pgvector schema (HNSW vector indexes)
mcp_servers/     8 MCP tool servers (parsing, search, scoring, feedback, eval, monitor, compliance)
docker-compose.yml  Postgres · Redis · MinIO · API · worker · web
```

**AI layer**

| Concern | Implementation |
|---|---|
| Extraction & explanations | Claude (`claude-opus-4-8`) with Pydantic-validated structured JSON |
| Embeddings / semantic search | Voyage AI `voyage-3` (1024-dim) in prod, deterministic local fallback in dev — stored in pgvector |
| Scoring | Deterministic hybrid: 35% semantic + 35% skills + 20% experience + 10% education → 0–100 + confidence |
| Fairness | Regex+heuristic PII/protected-attribute redaction **before** any AI call; schema whitelisting; fairness prompt rules |
| Feedback loop | approve/reject/override → privacy gate → labeled dataset export → evaluation metrics (MAE, agreement, P@5) |

## Quick start (Docker)

```bash
cp .env.example .env          # add your ANTHROPIC_API_KEY (and VOYAGE_API_KEY for prod embeddings)
docker compose up --build
```

- Web UI: http://localhost:3000 (register as recruiter or candidate)
- API docs: http://localhost:8000/docs
- MinIO console: http://localhost:9001

The Postgres schema in `db/init/001_schema.sql` is applied automatically on
first start. Create an admin by registering a user, then in psql:
`UPDATE users SET role='admin' WHERE email='you@example.com';`

## Instant demo — no Docker, no accounts (dev mode)

`backend/.env` ships with `DEV_MODE=true`: SQLite instead of Postgres,
in-process jobs instead of Redis, local disk instead of S3, heuristic parsers
when no `ANTHROPIC_API_KEY` is set, and auto-seeded demo data.

```powershell
# terminal 1 — API on :8000
cd backend
..\.venv\Scripts\python -m uvicorn app.main:app --port 8000

# terminal 2 — UI on :3000
cd frontend
npm run dev
```

Demo logins (password `demo12345`): `admin@demo.example.com`,
`recruiter@demo.example.com`, `candidate@demo.example.com`.
Delete `backend/dev.db` to reset and re-seed. Add your `ANTHROPIC_API_KEY`
to `backend/.env` to switch parsing/explanations from heuristics to Claude.

## Local development (no Docker)

```bash
# infra only
docker compose up db redis minio minio-init

# backend
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload            # API on :8000
arq app.workers.tasks.WorkerSettings     # background worker

# frontend
cd frontend && npm install && npm run dev  # UI on :3000
```

## Core flows

1. **Recruiter**: create/upload a JD → upload resumes → “Match all resumes” →
   ranked candidate list → open a match → review evidence → approve /
   reject / override.
2. **Candidate**: upload resume → “Find matching jobs” → ranked jobs with
   skill-growth hints.
3. **Admin**: platform stats, full audit trail, run evaluations, export the
   privacy-checked training dataset.

## API surface (summary)

| Method & path | Purpose |
|---|---|
| `POST /auth/register` · `POST /auth/login` · `GET /auth/me` | JWT auth, roles: admin/recruiter/hiring_manager/candidate |
| `POST /resumes` (file or text) · `GET /resumes[/{id}]` · `DELETE /resumes/{id}` | Resume upload → async parse/redact/embed |
| `POST /jobs` · `POST /jobs/upload` · `GET /jobs[/{id}]` · `PATCH /jobs/{id}/close` | JD create/upload → async parse/embed |
| `POST /matches` | One resume × one job (async scoring) |
| `POST /matches/batch` | One job × many resumes, or one resume × many jobs |
| `GET /matches/job/{id}` · `GET /matches/resume/{id}` · `GET /matches/{id}` | Rankings and match detail |
| `POST /feedback` | Human review: approve / reject / override / comment |
| `GET /admin/stats` · `/admin/audit-logs` · `POST /admin/evaluate` · `POST /admin/training/export` | Ops, audit, evaluation, training pipeline |
| `GET /health` · `GET /metrics` | Deployment monitoring |

## MCP tool servers

Eight stdio MCP servers in `mcp_servers/` expose the platform to AI agents:
resume_parser, jd_parser, embedding_search, match_scoring, feedback_training,
evaluation, deployment_monitor, compliance_audit. See
[mcp_servers/README.md](mcp_servers/README.md) for client config.

## Tests

```bash
cd backend && pip install -r requirements.txt && pytest
```

Unit tests cover the PII/fairness redaction layer, the matching algorithm
(bounds, ranking order, gaps, aliases, confidence), chunking, and auth — all
deterministic, no external services required.

## Production deployment notes

- **API/worker**: any container host (Fly.io, Render, ECS, Cloud Run). Run
  `uvicorn` and `arq` as separate services from the same image.
- **DB**: managed Postgres with pgvector (Neon, Supabase, RDS + pgvector).
- **Storage**: S3 or Cloudflare R2 — set `S3_*` env vars.
- **Frontend**: Vercel (`NEXT_PUBLIC_API_URL` → your API URL) or the included
  standalone Docker image.
- **Secrets**: set a strong `SECRET_KEY`; provision `ANTHROPIC_API_KEY` and
  `VOYAGE_API_KEY` (`EMBEDDING_PROVIDER=voyage`).
- **Monitoring**: `/health` (liveness + model version) and `/metrics`
  (request/error counters) — the `deployment_monitor_server` MCP wraps both.
- **Fine-tuning**: `/admin/training/export` produces the privacy-checked
  dataset once ≥50 labeled feedback examples exist; wire the export into your
  training infra of choice and bump `SCORING_VERSION` on deploy so audit logs
  distinguish model generations.
