from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    pass


# Lazy engine so importing app modules never requires a live DB driver
# (keeps unit tests and MCP servers dependency-light).
_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def _normalize_url(url: str) -> str:
    """Accept URLs as issued by managed Postgres providers (Neon, Supabase):
    force the asyncpg driver and translate libpq-only query params."""
    from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]
    parts = urlsplit(url)
    query = [
        ("ssl", v) if k == "sslmode" else (k, v)
        for k, v in parse_qsl(parts.query)
        if k != "channel_binding"  # libpq-only; asyncpg rejects it
    ]
    return urlunsplit(parts._replace(query=urlencode(query)))


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            _normalize_url(get_settings().database_url), pool_pre_ping=True
        )
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _sessionmaker


def new_session() -> AsyncSession:
    return get_sessionmaker()()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with new_session() as session:
        yield session
