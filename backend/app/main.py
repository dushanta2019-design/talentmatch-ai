import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import admin, auth, feedback, jobs, matches, resumes
from app.services.llm import model_version


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if settings.dev_mode:
        from app.dev_seed import bootstrap_dev

        await bootstrap_dev()
    else:
        if settings.auto_create_schema:
            from app.dev_seed import create_schema

            await create_schema()
        if settings.seed_demo:
            from app.dev_seed import seed_demo_data

            await seed_demo_data()
    yield


app = FastAPI(
    lifespan=lifespan,
    title="AI Resume Matching API",
    description=(
        "Decision-support system for resume/job matching. "
        "All scores are advisory — final hiring decisions are made by humans."
    ),
    version="1.0.0",
)

_origins = ["http://localhost:3000"]
if get_settings().frontend_origin:
    _origins.append(get_settings().frontend_origin.rstrip("/"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple in-process metrics for the deployment monitor.
_metrics = {"requests_total": 0, "errors_total": 0, "started_at": time.time()}


@app.middleware("http")
async def count_requests(request: Request, call_next):
    _metrics["requests_total"] += 1
    try:
        response = await call_next(request)
    except Exception:
        _metrics["errors_total"] += 1
        raise
    if response.status_code >= 500:
        _metrics["errors_total"] += 1
    return response


app.include_router(auth.router)
app.include_router(resumes.router)
app.include_router(jobs.router)
app.include_router(matches.router)
app.include_router(feedback.router)
app.include_router(admin.router)


@app.get("/health", tags=["monitoring"])
async def health():
    return {"status": "ok", "model_version": model_version()}


@app.get("/metrics", tags=["monitoring"])
async def metrics():
    return {
        **_metrics,
        "uptime_seconds": round(time.time() - _metrics["started_at"], 1),
    }
