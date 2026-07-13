import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_roles
from app.database import get_db
from app.models import Job, User
from app.queue import get_queue
from app.schemas import JobCreate, JobOut
from app.services import storage
from app.services.resume_parser import extract_text

router = APIRouter(prefix="/jobs", tags=["jobs"])

STAFF = ("admin", "recruiter", "hiring_manager")


@router.post("", response_model=JobOut, status_code=201)
async def create_job(
    body: JobCreate,
    user: User = Depends(require_roles(*STAFF)),
    db: AsyncSession = Depends(get_db),
):
    job = Job(
        created_by=user.id,
        title=body.title,
        company=body.company,
        location=body.location,
        employment_type=body.employment_type,
        description_raw=body.description,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    queue = await get_queue()
    await queue.enqueue_job("process_job", str(job.id))
    return job


@router.post("/upload", response_model=JobOut, status_code=201)
async def upload_job(
    file: UploadFile = File(...),
    title: str = Form(...),
    company: str | None = Form(default=None),
    user: User = Depends(require_roles(*STAFF)),
    db: AsyncSession = Depends(get_db),
):
    """Upload a JD file (PDF/DOCX/TXT); text is extracted server-side."""
    data = await file.read()
    text = extract_text(data, file.content_type or "", file.filename or "")
    if not text.strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Could not extract text")
    key = storage.upload_bytes(
        data, file.filename or "jd", file.content_type or "application/octet-stream", "jobs"
    )
    job = Job(created_by=user.id, title=title, company=company,
              description_raw=text, file_key=key)
    db.add(job)
    await db.commit()
    await db.refresh(job)
    queue = await get_queue()
    await queue.enqueue_job("process_job", str(job.id))
    return job


@router.get("", response_model=list[JobOut])
async def list_jobs(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    q = select(Job).order_by(Job.created_at.desc())
    if user.role == "candidate":
        q = q.where(Job.is_open.is_(True))
    return (await db.execute(q)).scalars().all()


@router.get("/{job_id}", response_model=JobOut)
async def get_job(
    job_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job = await db.get(Job, job_id)
    if job is None or (user.role == "candidate" and not job.is_open):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    return job


@router.patch("/{job_id}/close", response_model=JobOut)
async def close_job(
    job_id: uuid.UUID,
    user: User = Depends(require_roles(*STAFF)),
    db: AsyncSession = Depends(get_db),
):
    job = await db.get(Job, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    job.is_open = False
    await db.commit()
    await db.refresh(job)
    return job
