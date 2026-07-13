"""Audit logging — every AI action writes a row before results are served."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


async def log_event(
    db: AsyncSession,
    event_type: str,
    entity_type: str,
    entity_id: uuid.UUID | None = None,
    actor_id: uuid.UUID | None = None,
    model_version: str | None = None,
    input_hash: str | None = None,
    details: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_id=actor_id,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            model_version=model_version,
            input_hash=input_hash,
            details=details,
        )
    )
    await db.flush()
