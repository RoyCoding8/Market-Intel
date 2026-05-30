"""FastAPI application entry-point."""

from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()

import logging  # noqa: E402
import os  # noqa: E402
import sys  # noqa: E402
import asyncio  # noqa: E402
from contextlib import asynccontextmanager  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import AsyncIterator  # noqa: E402
from urllib.parse import unquote  # noqa: E402

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from starlette.staticfiles import StaticFiles  # noqa: E402

# Ensure project root is on sys.path so `contracts` and `engine` are importable
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from backend.middleware.auth import ApiKeyMiddleware  # noqa: E402
from backend.middleware.body_limit import BodyLimitMiddleware  # noqa: E402
from backend.middleware.rate_limit import RateLimitMiddleware  # noqa: E402
from backend.routes.analytics import router as analytics_router  # noqa: E402
from backend.routes.health import router as health_router  # noqa: E402
from backend.routes.jobs import router as jobs_router  # noqa: E402
from backend.routes.schedules import router as schedules_router  # noqa: E402
from contracts.api import CreateJobRequest, ScheduleConfig, ScheduleFrequency  # noqa: E402
from backend.services.database import Database  # noqa: E402
from backend.services.event_store import EventStore  # noqa: E402
from backend.services.job_manager import JobManager  # noqa: E402
from backend.services.scheduler import SchedulerService  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

def _resolve_pipeline():
    try:
        from engine.pipeline import run_pipeline
        logger.info("Using engine.pipeline.run_pipeline")
        return run_pipeline
    except ImportError:
        from backend.services.engine_stub import run_pipeline_stub
        logger.warning("engine.pipeline not found — using stub")
        return run_pipeline_stub

def _database_path_from_env() -> str:
    database_url = os.getenv("DATABASE_URL", "sqlite:///./data/market_intel.db")
    if database_url.startswith("sqlite:///"):
        return unquote(database_url.removeprefix("sqlite:///"))
    logger.warning("Unsupported DATABASE_URL %s; using local SQLite default", database_url)
    return "./data/market_intel.db"

def _cors_origins_from_env() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001")
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    if "*" in origins:
        logger.warning("Ignoring wildcard CORS origin; configure explicit origins instead")
        origins = [origin for origin in origins if origin != "*"]
    return origins or ["http://localhost:3000"]

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup / shutdown lifecycle hook."""
    database: Database = app.state.database
    job_manager: JobManager = app.state.job_manager
    scheduler: SchedulerService = app.state.scheduler
    await database.initialize()
    await job_manager.initialize()
    scheduler.start()
    from backend.routes.schedules import _scheduled_callback

    for row in await database.list_schedules():
        if not row.get("enabled"):
            continue
        try:
            CreateJobRequest.model_validate_json(row["request_json"])
            schedule = ScheduleConfig(
                frequency=ScheduleFrequency(row["frequency"]),
                cron_expression=row["cron_expression"],
            )
            scheduler.add_scheduled_job(
                row["job_id"],
                schedule,
                _scheduled_callback,
                app=app,
            )
        except Exception as exc:
            logger.warning("Failed to restore schedule %s: %s", row.get("id"), exc)
    logger.info("Application started")
    try:
        yield
    finally:
        tasks = list(getattr(app.state, "background_tasks", set()))
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        scheduler.shutdown()
        await database.close()
        logger.info("Application shut down")

def create_app(
    *,
    rate_limit_general: int = 100,
    rate_limit_job_creation: int = 10,
    rate_limit_window: float = 60.0,
) -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title="Market Intelligence Agent",
        version="0.3.0",
        lifespan=lifespan,
    )

    app.add_middleware(ApiKeyMiddleware)
    app.add_middleware(BodyLimitMiddleware)
    app.add_middleware(
        RateLimitMiddleware,
        general_limit=rate_limit_general,
        job_creation_limit=rate_limit_job_creation,
        window=rate_limit_window,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins_from_env(),
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["*"],
    )

    app.state.database = Database(_database_path_from_env())
    app.state.job_manager = JobManager(app.state.database)
    app.state.event_store = EventStore()
    app.state.scheduler = SchedulerService()
    app.state.run_pipeline = _resolve_pipeline()
    app.state.background_tasks = set()

    # Concurrent job cap — prevents resource exhaustion from parallel pipelines.
    max_concurrent = int(os.getenv("MAX_CONCURRENT_JOBS", "5"))
    app.state.job_semaphore = asyncio.Semaphore(max_concurrent)
    logger.info("Concurrent job limit: %d", max_concurrent)

    # Pipeline timeout (seconds).  0 = no timeout.
    app.state.pipeline_timeout = int(os.getenv("PIPELINE_TIMEOUT_SECONDS", "600"))
    logger.info("Pipeline timeout: %ds", app.state.pipeline_timeout)

    app.include_router(health_router)
    app.include_router(jobs_router)
    app.include_router(analytics_router)
    app.include_router(schedules_router)

    export_dir = os.path.join(".", "data", "exports")
    os.makedirs(export_dir, exist_ok=True)
    app.mount("/data/exports", StaticFiles(directory=export_dir), name="exports")

    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
