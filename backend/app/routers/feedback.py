from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_roles
from app.database import get_db
from app.models import Feedback, Match, User
from app.schemas import FeedbackCreate, FeedbackOut
from app.services import audit

router = APIRouter(prefix="/feedback", tags=["feedback"])

REVIEWERS = ("admin", "recruiter", "hiring_manager")


@router.post("", response_model=FeedbackOut, status_code=201)
async def submit_feedback(
    body: FeedbackCreate,
    user: User = Depends(require_roles(*REVIEWERS)),
    db: AsyncSession = Depends(get_db),
):
    """Human review of an AI match: approve, reject, override, or comment.

    This is the human-in-the-loop control required by the compliance policy —
    the AI never makes a final decision.
    """
    match = await db.get(Match, body.match_id)
    if match is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match not found")
    if body.action == "override" and body.label_score is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "override requires label_score")

    fb = Feedback(
        match_id=match.id, user_id=user.id, action=body.action,
        label_score=body.label_score, comment=body.comment,
    )
    db.add(fb)

    if body.action == "approve":
        match.review_status = "approved"
    elif body.action == "reject":
        match.review_status = "rejected"
    elif body.action == "override":
        match.review_status = "overridden"
        match.override_score = body.label_score
    match.reviewed_by = user.id

    await audit.log_event(
        db, f"feedback.{body.action}", "match", match.id, actor_id=user.id,
        details={"label_score": body.label_score},
    )
    await db.commit()
    await db.refresh(fb)
    return fb
