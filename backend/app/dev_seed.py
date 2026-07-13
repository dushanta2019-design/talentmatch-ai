"""Schema bootstrap + demo seed.

- create_schema(): CREATE EXTENSION vector (Postgres) + all tables. Used in
  dev mode and when AUTO_CREATE_SCHEMA=true (e.g. fresh Neon database).
- seed_demo_data(): demo accounts + sample jobs/resumes, only if the users
  table is empty. Used in dev mode and when SEED_DEMO=true.

Demo logins (password for all: demo12345):
  admin@demo.example.com · recruiter@demo.example.com · candidate@demo.example.com
"""

import logging

from sqlalchemy import func, select, text

from app.auth import hash_password
from app.database import Base, get_engine, new_session
from app.models import Job, Resume, User

log = logging.getLogger("dev_seed")

DEMO_PASSWORD = "demo12345"

DEMO_JOBS = [
    {
        "title": "Senior Python Backend Engineer",
        "company": "Northwind Labs",
        "location": "Remote",
        "description_raw": (
            "We are hiring a Senior Python Backend Engineer.\n\n"
            "Requirements:\n"
            "- 5+ years of backend development experience\n"
            "- Strong Python, FastAPI or Django\n"
            "- PostgreSQL, Redis, Docker, AWS\n"
            "- Bachelor's degree in Computer Science or equivalent\n\n"
            "Preferred / nice to have:\n"
            "- Kubernetes, Terraform, CI/CD pipelines\n"
            "- Experience with machine learning systems\n"
        ),
    },
    {
        "title": "Frontend Developer (React)",
        "company": "Brightline",
        "location": "Hybrid — Colombo",
        "description_raw": (
            "Frontend Developer to build modern web apps.\n\n"
            "Requirements:\n"
            "- 3+ years with JavaScript and TypeScript\n"
            "- React, HTML, CSS, REST APIs\n\n"
            "Preferred:\n"
            "- Next.js, GraphQL, Figma collaboration\n"
        ),
    },
]

DEMO_RESUMES = [
    {
        "file_name": "backend-candidate.txt",
        "raw_text": (
            "Kasun Perera\n"
            "Email: kasun.p@example.com | Phone: +94 77 123 4567\n\n"
            "Senior Backend Engineer with 7 years of experience building "
            "microservices in Python (FastAPI, Django) on AWS. Deep experience "
            "with PostgreSQL, Redis, Docker and Kubernetes. Led CI/CD adoption "
            "and mentored a team of 5 engineers.\n\n"
            "Education: Bachelor of Science in Computer Science\n"
            "Certifications: AWS Certified Solutions Architect\n"
        ),
    },
    {
        "file_name": "frontend-candidate.txt",
        "raw_text": (
            "Amara Silva\n"
            "Email: amara.s@example.com\n\n"
            "Frontend developer with 4 years of experience. Expert in "
            "JavaScript, TypeScript, React and Next.js. Built design systems "
            "with Figma, integrated REST and GraphQL APIs.\n\n"
            "Education: Bachelor of Information Technology\n"
        ),
    },
    {
        "file_name": "designer-candidate.txt",
        "raw_text": (
            "Nuwan Fernando\n\n"
            "Graphic designer with 2 years of experience in Photoshop, "
            "Illustrator and Figma. Diploma in Visual Design.\n"
        ),
    },
]


async def create_schema() -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        if engine.dialect.name == "postgresql":
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)


async def bootstrap_dev() -> None:
    await create_schema()
    await seed_demo_data()


async def seed_demo_data() -> None:
    async with new_session() as db:
        n_users = (await db.execute(select(func.count()).select_from(User))).scalar_one()
        if n_users > 0:
            return

        pw = hash_password(DEMO_PASSWORD)
        admin = User(email="admin@demo.example.com", password_hash=pw,
                     full_name="Demo Admin", role="admin")
        recruiter = User(email="recruiter@demo.example.com", password_hash=pw,
                         full_name="Demo Recruiter", role="recruiter")
        candidate = User(email="candidate@demo.example.com", password_hash=pw,
                         full_name="Demo Candidate", role="candidate")
        db.add_all([admin, recruiter, candidate])
        await db.flush()

        job_ids, resume_ids = [], []
        for j in DEMO_JOBS:
            job = Job(created_by=recruiter.id, **j)
            db.add(job)
            await db.flush()
            job_ids.append(str(job.id))
        for r in DEMO_RESUMES:
            resume = Resume(owner_id=candidate.id, **r)
            db.add(resume)
            await db.flush()
            resume_ids.append(str(resume.id))
        await db.commit()

    # Parse everything inline (heuristic parsers when no API key is set).
    from app.queue import get_queue

    queue = await get_queue()
    for jid in job_ids:
        await queue.enqueue_job("process_job", jid)
    for rid in resume_ids:
        await queue.enqueue_job("process_resume", rid)

    log.info("Seeded demo data — logins: admin/recruiter/candidate@demo.example.com "
             "(password: %s)", DEMO_PASSWORD)
