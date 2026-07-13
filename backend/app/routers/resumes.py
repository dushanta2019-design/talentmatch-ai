import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import Resume, User
from app.queue import get_queue
from app.schemas import ResumeOut
from app.services import storage

router = APIRouter(prefix="/resumes", tags=["resumes"])

ALLOWED_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}
MAX_SIZE = 10 * 1024 * 1024


def _can_view(user: User, resume: Resume) -> bool:
    return user.role in ("admin", "recruiter", "hiring_manager") or resume.owner_id == user.id


@router.post("", response_model=ResumeOut, status_code=201)
async def upload_resume(
    file: UploadFile | None = File(default=None),
    text: str | None = Form(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a resume file (PDF/DOCX/TXT) or paste raw text."""
    if file is None and not text:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Provide a file or text")

    resume = Resume(owner_id=user.id, status="pending")
    if file is not None:
        if file.content_type not in ALLOWED_TYPES:
            raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                                f"Unsupported type {file.content_type}")
        data = await file.read()
        if len(data) > MAX_SIZE:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Max 10 MB")
        resume.file_key = storage.upload_bytes(
            data, file.filename or "resume", file.content_type, "resumes"
        )
        resume.file_name = file.filename
        resume.mime_type = file.content_type
    else:
        resume.raw_text = text
        resume.file_name = "pasted-text.txt"

    db.add(resume)
    await db.commit()
    await db.refresh(resume)

    queue = await get_queue()
    await queue.enqueue_job("process_resume", str(resume.id))
    return resume


@router.get("", response_model=list[ResumeOut])
async def list_resumes(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    q = select(Resume).order_by(Resume.created_at.desc())
    if user.role == "candidate":
        q = q.where(Resume.owner_id == user.id)
    return (await db.execute(q)).scalars().all()


@router.get("/{resume_id}", response_model=ResumeOut)
async def get_resume(
    resume_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resume = await db.get(Resume, resume_id)
    if resume is None or not _can_view(user, resume):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Resume not found")
    return resume


@router.delete("/{resume_id}", status_code=204)
async def delete_resume(
    resume_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resume = await db.get(Resume, resume_id)
    if resume is None or (resume.owner_id != user.id and user.role != "admin"):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Resume not found")
    await db.delete(resume)
    await db.commit()
