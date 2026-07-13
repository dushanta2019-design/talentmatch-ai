import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_roles
from app.database import get_db
from app.models import Job, Match, Resume, User
from app.queue import get_queue
from app.schemas import BatchMatchRequest, MatchOut, MatchRequest, RankedMatchOut

router = APIRouter(prefix="/matches", tags=["matches"])

STAFF = ("admin", "recruiter", "hiring_manager")


async def _upsert_match(db: AsyncSession, resume_id: uuid.UUID, job_id: uuid.UUID) -> Match:
    # Portable upsert (works on Postgres and SQLite dev mode). The unique
    # constraint on (resume_id, job_id) still guards against races.
    existing = (
        await db.execute(
            select(Match).where(Match.resume_id == resume_id, Match.job_id == job_id)
        )
    ).scalar_one_or_none()
    if existing is not None:
        existing.status = "pending"
        existing.error = None
        await db.commit()
        return existing
    match = Match(resume_id=resume_id, job_id=job_id, status="pending")
    db.add(match)
    await db.commit()
    await db.refresh(match)
    return match


@router.post("", response_model=MatchOut, status_code=202)
async def request_match(
    body: MatchRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Match ONE resume against ONE job. Scoring runs asynchronously."""
    resume = await db.get(Resume, body.resume_id)
    job = await db.get(Job, body.job_id)
    if resume is None or job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Resume or job not found")
    if user.role == "candidate" and resume.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your resume")

    match = await _upsert_match(db, body.resume_id, body.job_id)
    queue = await get_queue()
    await queue.enqueue_job("score_match", str(match.id))
    return match


@router.post("/batch", response_model=list[MatchOut], status_code=202)
async def request_batch_match(
    body: BatchMatchRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """One JD → many resumes (staff), or one resume → many JDs (any role)."""
    matches: list[Match] = []
    queue = await get_queue()

    if body.job_id is not None:
        if user.role not in STAFF:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Recruiter access required")
        resumes = (
            (await db.execute(
                select(Resume.id).where(Resume.status == "ready").limit(body.limit)
            )).scalars().all()
        )
        for rid in resumes:
            matches.append(await _upsert_match(db, rid, body.job_id))
    elif body.resume_id is not None:
        resume = await db.get(Resume, body.resume_id)
        if resume is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Resume not found")
        if user.role == "candidate" and resume.owner_id != user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your resume")
        jobs = (
            (await db.execute(
                select(Job.id).where(Job.status == "ready", Job.is_open.is_(True))
                .limit(body.limit)
            )).scalars().all()
        )
        for jid in jobs:
            matches.append(await _upsert_match(db, body.resume_id, jid))
    else:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "job_id or resume_id required")

    for m in matches:
        await queue.enqueue_job("score_match", str(m.id))
    return matches


@router.get("/job/{job_id}", response_model=list[RankedMatchOut])
async def rank_candidates_for_job(
    job_id: uuid.UUID,
    user: User = Depends(require_roles(*STAFF)),
    db: AsyncSession = Depends(get_db),
):
    """Ranked candidates for a job (highest score first)."""
    rows = (
        await db.execute(
            select(Match, Resume.file_name)
            .join(Resume, Match.resume_id == Resume.id)
            .where(Match.job_id == job_id)
            .order_by(Match.overall_score.desc().nulls_last())
        )
    ).all()
    out = []
    for match, file_name in rows:
        item = RankedMatchOut.model_validate(match)
        item.resume_file_name = file_name
        out.append(item)
    return out


@router.get("/resume/{resume_id}", response_model=list[RankedMatchOut])
async def rank_jobs_for_resume(
    resume_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Ranked jobs for a candidate (highest score first)."""
    resume = await db.get(Resume, resume_id)
    if resume is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Resume not found")
    if user.role == "candidate" and resume.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your resume")

    rows = (
        await db.execute(
            select(Match, Job.title)
            .join(Job, Match.job_id == Job.id)
            .where(Match.resume_id == resume_id)
            .order_by(Match.overall_score.desc().nulls_last())
        )
    ).all()
    out = []
    for match, title in rows:
        item = RankedMatchOut.model_validate(match)
        item.job_title = title
        out.append(item)
    return out


@router.get("/{match_id}", response_model=MatchOut)
async def get_match(
    match_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    match = await db.get(Match, match_id)
    if match is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match not found")
    if user.role == "candidate":
        resume = await db.get(Resume, match.resume_id)
        if resume is None or resume.owner_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Match not found")
    return match
