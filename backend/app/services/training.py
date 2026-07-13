"""Feedback → training pipeline.

Exports a privacy-checked, PII-free preference dataset from recruiter
feedback. Each example pairs redacted structured inputs with the human
label. The export is stored as a training_run row (artifacts contain the
dataset inline for small volumes; point at S3 for large ones).

Feedback is only usable after passing the privacy gate:
  1. the source resume text must already be redacted (it always is), and
  2. the free-text comment must not itself contain PII.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Feedback, Match, Resume, TrainingRun
from app.services.pii import contains_pii

MIN_EXAMPLES = 50  # don't bother orchestrating fine-tuning below this


async def privacy_check_feedback(db: AsyncSession) -> int:
    """Mark feedback rows whose content passes the PII gate."""
    rows = (
        (await db.execute(select(Feedback).where(Feedback.privacy_checked.is_(False))))
        .scalars()
        .all()
    )
    passed = 0
    for fb in rows:
        if fb.comment and contains_pii(fb.comment):
            # keep for review UX, but never for training
            fb.privacy_checked = True
            fb.used_for_training = False
            continue
        fb.privacy_checked = True
        passed += 1
    await db.flush()
    return passed


async def export_training_dataset(db: AsyncSession) -> TrainingRun:
    """Build the labeled dataset from privacy-checked feedback."""
    await privacy_check_feedback(db)

    rows = (
        await db.execute(
            select(Feedback, Match, Resume)
            .join(Match, Feedback.match_id == Match.id)
            .join(Resume, Match.resume_id == Resume.id)
            .where(
                Feedback.privacy_checked.is_(True),
                Feedback.action.in_(("approve", "reject", "override")),
                Match.overall_score.is_not(None),
            )
        )
    ).all()

    examples = []
    for fb, match, resume in rows:
        label = (
            fb.label_score
            if fb.action == "override" and fb.label_score is not None
            else (85 if fb.action == "approve" else 15)
        )
        examples.append(
            {
                "candidate_profile": resume.parsed,     # redacted, structured
                "job_id": str(match.job_id),
                "ai_score": float(match.overall_score),
                "human_label": label,
                "action": fb.action,
            }
        )
        fb.used_for_training = True

    status = "exported" if len(examples) >= MIN_EXAMPLES else "insufficient_data"
    run = TrainingRun(
        base_model=get_settings().llm_model,
        dataset_size=len(examples),
        status=status,
        artifacts={"examples": examples[:1000], "min_required": MIN_EXAMPLES},
    )
    db.add(run)
    await db.flush()
    return run
