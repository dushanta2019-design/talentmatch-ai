"""Background jobs (arq + Redis): parsing, embedding, and scoring.

Enqueue with:  await redis.enqueue_job("process_resume", str(resume_id))
"""

import uuid

from arq.connections import RedisSettings

from app.config import get_settings
from app.database import new_session
from app.models import Job, Match, Resume, ResumeChunk
from app.schemas import ParsedJob, ParsedResume
from app.services import audit, storage
from app.services.embeddings import chunk_text, embed_text, embed_texts
from app.services.explanation import explain_match
from app.services.jd_parser import parse_job_text
from app.services.llm import model_version
from app.services.matching import compute_match
from app.services.pii import input_hash
from app.services.resume_parser import extract_text, parse_resume_text


async def process_resume(ctx, resume_id: str) -> None:
    async with new_session() as db:
        resume = await db.get(Resume, uuid.UUID(resume_id))
        if resume is None:
            return
        resume.status = "processing"
        await db.commit()
        try:
            if resume.raw_text is None and resume.file_key:
                data = storage.download_bytes(resume.file_key)
                resume.raw_text = extract_text(
                    data, resume.mime_type or "", resume.file_name or ""
                )

            redacted, parsed = parse_resume_text(resume.raw_text or "")
            resume.redacted_text = redacted
            resume.parsed = parsed.model_dump()
            resume.embedding = embed_text(redacted)

            chunks = chunk_text(redacted)
            if chunks:
                vectors = embed_texts(chunks)
                for i, (content, vec) in enumerate(zip(chunks, vectors)):
                    db.add(
                        ResumeChunk(
                            resume_id=resume.id, chunk_index=i,
                            content=content, embedding=vec,
                        )
                    )

            resume.status = "ready"
            await audit.log_event(
                db, "resume.parsed", "resume", resume.id,
                actor_id=resume.owner_id, model_version=model_version(),
                input_hash=input_hash(redacted),
                details={"skills_found": len(parsed.skills)},
            )
        except Exception as exc:  # surface failure to the UI instead of dying silently
            resume.status = "failed"
            resume.error = str(exc)[:2000]
        await db.commit()


async def process_job(ctx, job_id: str) -> None:
    async with new_session() as db:
        job = await db.get(Job, uuid.UUID(job_id))
        if job is None:
            return
        job.status = "processing"
        await db.commit()
        try:
            parsed = parse_job_text(job.description_raw, job.title)
            job.parsed = parsed.model_dump()
            job.embedding = embed_text(job.description_raw)
            job.status = "ready"
            await audit.log_event(
                db, "job.parsed", "job", job.id,
                actor_id=job.created_by, model_version=model_version(),
                input_hash=input_hash(job.description_raw),
                details={"required_skills": len(parsed.required_skills)},
            )
        except Exception as exc:
            job.status = "failed"
            job.error = str(exc)[:2000]
        await db.commit()


async def score_match(ctx, match_id: str) -> None:
    async with new_session() as db:
        match = await db.get(Match, uuid.UUID(match_id))
        if match is None:
            return
        resume = await db.get(Resume, match.resume_id)
        job = await db.get(Job, match.job_id)
        if resume is None or job is None or not resume.parsed or not job.parsed:
            match.status = "failed"
            match.error = "Resume or job not parsed yet"
            await db.commit()
            return
        try:
            parsed_resume = ParsedResume.model_validate(resume.parsed)
            parsed_job = ParsedJob.model_validate(job.parsed)

            resume_emb = list(resume.embedding) if resume.embedding is not None else None
            job_emb = list(job.embedding) if job.embedding is not None else None
            scores = compute_match(parsed_resume, parsed_job, resume_emb, job_emb)
            explanation = explain_match(parsed_resume, parsed_job, scores)

            match.overall_score = scores.overall
            match.confidence = scores.confidence
            match.semantic_score = scores.semantic
            match.skills_score = scores.skills
            match.experience_score = scores.experience
            match.education_score = scores.education
            match.matched_skills = scores.matched_skills
            match.missing_skills = scores.missing_skills
            match.gaps = scores.gaps
            match.explanation = explanation.model_dump()
            match.model_version = model_version()
            match.status = "scored"

            await audit.log_event(
                db, "match.scored", "match", match.id,
                model_version=model_version(),
                input_hash=input_hash(resume.redacted_text or "", job.description_raw),
                details={
                    "overall_score": scores.overall,
                    "confidence": scores.confidence,
                    "resume_id": str(resume.id),
                    "job_id": str(job.id),
                },
            )
        except Exception as exc:
            match.status = "failed"
            match.error = str(exc)[:2000]
        await db.commit()


class WorkerSettings:
    functions = [process_resume, process_job, score_match]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    max_jobs = 10
    job_timeout = 300
