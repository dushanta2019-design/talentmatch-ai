from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_roles
from app.database import get_db
from app.models import AuditLog, EvalRun, Feedback, Job, Match, Resume, TrainingRun, User
from app.schemas import AuditLogOut, EvalRunOut, UserOut
from app.services.evaluation import run_evaluation
from app.services.training import export_training_dataset

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats")
async def stats(
    user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    async def count(model, *where):
        q = select(func.count()).select_from(model)
        for w in where:
            q = q.where(w)
        return (await db.execute(q)).scalar_one()

    return {
        "users": await count(User),
        "resumes": await count(Resume),
        "jobs": await count(Job),
        "matches_scored": await count(Match, Match.status == "scored"),
        "matches_failed": await count(Match, Match.status == "failed"),
        "matches_reviewed": await count(Match, Match.review_status != "unreviewed"),
        "feedback_items": await count(Feedback),
        "avg_score": float(
            (await db.execute(select(func.avg(Match.overall_score)))).scalar() or 0
        ),
    }


@router.get("/users", response_model=list[UserOut])
async def list_users(
    user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    return (await db.execute(select(User).order_by(User.created_at.desc()))).scalars().all()


@router.get("/audit-logs", response_model=list[AuditLogOut])
async def audit_logs(
    limit: int = Query(default=100, le=500),
    user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    return (
        (await db.execute(
            select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
        )).scalars().all()
    )


@router.post("/evaluate", response_model=EvalRunOut)
async def evaluate(
    user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Run the evaluation pipeline against accumulated recruiter feedback."""
    run = await run_evaluation(db)
    await db.commit()
    return run


@router.get("/evaluations", response_model=list[EvalRunOut])
async def evaluations(
    user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    return (
        (await db.execute(select(EvalRun).order_by(EvalRun.created_at.desc()).limit(50)))
        .scalars().all()
    )


@router.post("/training/export")
async def training_export(
    user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Privacy-check feedback and export the fine-tuning dataset."""
    run = await export_training_dataset(db)
    await db.commit()
    return {
        "id": str(run.id),
        "status": run.status,
        "dataset_size": run.dataset_size,
        "base_model": run.base_model,
    }


@router.get("/training/runs")
async def training_runs(
    user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    runs = (
        (await db.execute(select(TrainingRun).order_by(TrainingRun.created_at.desc()).limit(50)))
        .scalars().all()
    )
    return [
        {"id": str(r.id), "status": r.status, "dataset_size": r.dataset_size,
         "base_model": r.base_model, "created_at": r.created_at.isoformat()}
        for r in runs
    ]
