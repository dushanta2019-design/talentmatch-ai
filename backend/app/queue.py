"""Job queue abstraction.

Production: arq + Redis (separate worker process).
Dev mode:   tasks run in-process on the API's event loop — no Redis needed.
"""

import asyncio

from app.config import get_settings

_pool = None
_background: set[asyncio.Task] = set()


class InlineQueue:
    """Runs worker functions as asyncio tasks in the API process."""

    async def enqueue_job(self, name: str, *args) -> None:
        from app.workers import tasks

        fn = getattr(tasks, name)
        task = asyncio.create_task(fn(None, *args))
        _background.add(task)
        task.add_done_callback(_background.discard)


async def get_queue():
    settings = get_settings()
    if settings.dev_mode or settings.queue_backend == "inline":
        return InlineQueue()

    global _pool
    if _pool is None:
        from arq import create_pool
        from arq.connections import RedisSettings

        _pool = await create_pool(RedisSettings.from_dsn(get_settings().redis_url))
    return _pool
