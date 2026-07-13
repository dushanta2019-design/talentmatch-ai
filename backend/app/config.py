from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    secret_key: str = "dev-secret-do-not-use-in-prod"
    access_token_expire_minutes: int = 480

    # Dev mode: SQLite + in-process jobs + local file storage + seeded demo
    # data. No Postgres/Redis/MinIO/API keys needed. Never use in production.
    dev_mode: bool = False

    database_url: str = "postgresql+asyncpg://resumeai:resumeai@localhost:5432/resumeai"
    redis_url: str = "redis://localhost:6379/0"

    # "arq" (Redis-backed worker) or "inline" (in-process asyncio — good for
    # single-instance deployments like Render free tier).
    queue_backend: str = "arq"
    # Create extension/tables on startup (managed Postgres like Neon) and
    # optionally seed demo accounts/data on an empty database.
    auto_create_schema: bool = False
    seed_demo: bool = False
    # Extra allowed CORS origin for the deployed frontend, e.g. Vercel URL.
    frontend_origin: str = ""

    storage_backend: str = "s3"  # "s3" | "local"
    local_storage_dir: str = "./data/files"

    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "resume-files"
    s3_region: str = "us-east-1"

    anthropic_api_key: str = ""
    llm_model: str = "claude-opus-4-8"

    embedding_provider: str = "local"  # "voyage" | "local"
    voyage_api_key: str = ""
    embedding_model: str = "voyage-3"
    embedding_dim: int = 1024

    # Matching weights (must sum to 1.0)
    weight_semantic: float = 0.35
    weight_skills: float = 0.35
    weight_experience: float = 0.20
    weight_education: float = 0.10

    scoring_version: str = "hybrid-v1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
