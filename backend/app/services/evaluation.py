"""Model evaluation against recruiter feedback.

Metrics:
- mae:            |ai_score − recruiter_label| averaged over override feedback
- agreement_rate: share of approve/reject actions consistent with a 50-point
                  decision threshold on the AI score
- precision_at_5: of the top-5 AI-ranked candidates per job, how many the
                  recruiter approved
"""

import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import EvalRun, Feedback, Match
from app.services.llm import model_version


async def run_evaluation(db: AsyncSession) -> EvalRun:
    rows = (
        await db.execute(
            select(Feedback, Match)
            .join(Match, Feedback.match_id == Match.id)
            .where(Match.overall_score.is_not(None))
        )
    ).all()

    abs_errors: list[float] = []
    agree, decided = 0, 0
    per_job_scores: dict[uuid.UUID, list[tuple[float, bool]]] = defaultdict(list)

    for fb, match in rows:
        score = float(match.overall_score)
        if fb.action == "override" and fb.label_score is not None:
            abs_errors.append(abs(score - fb.label_score))
        if fb.action in ("approve", "reject"):
            decided += 1
            ai_positive = score >= 50.0
            if (fb.action == "approve") == ai_positive:
                agree += 1
            per_job_scores[match.job_id].append((score, fb.action == "approve"))

    p_at_5_values = []
    for scored in per_job_scores.values():
        top5 = sorted(scored, key=lambda t: t[0], reverse=True)[:5]
        if top5:
            p_at_5_values.append(sum(1 for _, ok in top5 if ok) / len(top5))

    metrics = {
        "mae": round(sum(abs_errors) / len(abs_errors), 2) if abs_errors else None,
        "agreement_rate": round(agree / decided, 3) if decided else None,
        "precision_at_5": round(sum(p_at_5_values) / len(p_at_5_values), 3)
        if p_at_5_values
        else None,
        "n_override_labels": len(abs_errors),
        "n_decisions": decided,
    }

    run = EvalRun(model_version=model_version(), dataset_size=len(rows), metrics=metrics)
    db.add(run)
    await db.flush()
    return run
