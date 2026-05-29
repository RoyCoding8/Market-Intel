"""Job CRUD + SSE stream endpoints."""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from contracts.api import (
    CancelJobResponse,
    Citation,
    ConfidenceLevel,
    CreateJobRequest,
    CreateJobResponse,
    ExportRequest,
    ExportResponse,
    Finding,
    IntelligenceReport,
    JobListResponse,
    JobStatus,
    JobStatusResponse,
    ReportResponse,
)
from contracts.engine import PipelineContext, PipelineState, ReportOutput
from contracts.events import AgentEvent, EventType

logger = logging.getLogger(__name__)

router = APIRouter(tags=["jobs"])
DEFAULT_LLM_MODEL = "openai/mimo-v2.5-pro"


def _env_int(name: str, default: int, *, min_value: int, max_value: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        logger.warning("Invalid integer for %s; using %d", name, default)
        return default
    if not min_value <= value <= max_value:
        logger.warning("Out-of-range integer for %s=%d; using %d", name, value, default)
        return default
    return value


def _configured_pipeline_kwargs() -> dict[str, int | str]:
    return {
        "llm_model": os.getenv("LLM_MODEL", DEFAULT_LLM_MODEL),
        "max_pages_per_competitor": _env_int("MAX_PAGES_PER_COMPETITOR", 20, min_value=1, max_value=100),
        "verification_passes": _env_int("VERIFICATION_PASSES", 2, min_value=1, max_value=10),
    }


def _focus_areas_from_request(body: CreateJobRequest) -> list[str]:
    focus_areas: list[str] = []
    for comp in body.competitors:
        focus_areas.extend(comp.focus_areas)
    focus_areas = list(dict.fromkeys(focus_areas))
    return focus_areas or ["pricing", "features", "team", "news"]


def _start_background_task(request: Request, coro) -> None:
    task = asyncio.create_task(coro)
    tasks = getattr(request.app.state, "background_tasks", None)
    if tasks is not None:
        tasks.add(task)
        task.add_done_callback(tasks.discard)


class _JobProgressEmitter:
    """Forward engine events while keeping backend job state in sync."""

    def __init__(self, job_mgr: Any, event_store: Any) -> None:
        self._job_mgr = job_mgr
        self._event_store = event_store

    async def emit(self, event: AgentEvent) -> None:
        await self._sync_job_state(event)
        if event.event_type in (EventType.JOB_STARTED, EventType.JOB_COMPLETED, EventType.JOB_FAILED, EventType.JOB_CANCELLED):
            return
        await self._event_store.publish(event)

    async def _sync_job_state(self, event: AgentEvent) -> None:
        if event.event_type == EventType.STEP_STARTED:
            message = event.message.lower()
            if "scraping" in message:
                await self._job_mgr.update_status(event.job_id, JobStatus.SCRAPING)
                await self._job_mgr.update_progress(event.job_id, progress=0.10, current_step="scraping")
            elif "analyzing" in message:
                await self._job_mgr.update_status(event.job_id, JobStatus.ANALYZING)
                await self._job_mgr.update_progress(event.job_id, progress=0.35, current_step="analyzing")
            elif "verifying" in message:
                await self._job_mgr.update_status(event.job_id, JobStatus.VERIFYING)
                await self._job_mgr.update_progress(event.job_id, progress=0.65, current_step="verifying")
            elif "reporting" in message:
                await self._job_mgr.update_status(event.job_id, JobStatus.GENERATING_REPORT)
                await self._job_mgr.update_progress(event.job_id, progress=0.85, current_step="generating_report")
        elif event.event_type == EventType.PAGE_SCRAPED:
            rec = await self._job_mgr.get_job(event.job_id)
            if rec:
                await self._job_mgr.update_progress(event.job_id, pages_scraped=rec.pages_scraped + 1)
        elif event.event_type == EventType.FINDING_FOUND:
            rec = await self._job_mgr.get_job(event.job_id)
            if rec:
                await self._job_mgr.update_progress(event.job_id, findings_count=rec.findings_count + 1)
        elif event.event_type == EventType.STEP_FAILED:
            await self._job_mgr.update_progress(event.job_id, current_step="failed")
        elif event.event_type == EventType.JOB_FAILED:
            await self._job_mgr.set_error(event.job_id, event.message)


# ── Helpers ───────────────────────────────────────────────────────────────


def _report_output_to_intelligence_report(
    job_id: str,
    report_output: ReportOutput,
    competitor_urls: list[str],
    verification_passes: int = 0,
) -> IntelligenceReport:
    """Convert an engine ReportOutput into an API IntelligenceReport.

    Args:
        job_id: The job ID.
        report_output: The engine's ReportOutput.
        competitor_urls: List of competitor URLs from the pipeline context.

    Returns:
        IntelligenceReport suitable for saving and API responses.
    """
    from datetime import datetime, timezone

    from contracts.api import ComparisonTable, ComparisonRow
    now = datetime.now(timezone.utc)

    def _to_citation(c) -> Citation:
        if isinstance(c, dict):
            return Citation(url=c.get("url", ""), title=c.get("title"),
                            quote=c.get("quote", ""), accessed_at=now, confidence=ConfidenceLevel.HIGH)
        return c

    def _to_finding(i: int, f: dict) -> Finding:
        try:
            conf_level = ConfidenceLevel(f.get("confidence", "medium"))
        except ValueError:
            conf_level = ConfidenceLevel.MEDIUM
        return Finding(
            id=f.get("id", f"finding-{i}"), title=f.get("title", "Untitled"),
            summary=f.get("summary", ""), category=f.get("category", "general"),
            confidence=conf_level, confidence_score=f.get("confidence_score", 0.5),
            citations=[_to_citation(c) for c in f.get("citations", [])],
            competitor_ids=competitor_urls, impact=f.get("impact"), recommendation=f.get("recommendation"),
        )

    def _to_table(t: dict) -> ComparisonTable:
        rows = [ComparisonRow(dimension=r.get("dimension", ""), values=r.get("values", {}),
                              winner=r.get("winner"))
                for r in t.get("rows", []) if isinstance(r, dict)]
        return ComparisonTable(title=t.get("title", ""), dimensions=[r.dimension for r in rows],
                               rows=rows, competitor_ids=competitor_urls)

    findings = [_to_finding(i, f) for i, f in enumerate(report_output.findings)]
    comparison_tables = [_to_table(t) for t in report_output.comparison_tables]

    return IntelligenceReport(
        id=f"report-{job_id}",
        title=f"Intelligence Report: {', '.join(competitor_urls)}",
        created_at=now, competitors=[], findings=findings,
        comparison_tables=comparison_tables,
        executive_summary=report_output.executive_summary,
        trend_analysis=report_output.trend_analysis,
        recommendations=report_output.recommendations,
        total_sources=report_output.total_sources,
        verification_passes=verification_passes,
    )


async def _run_job_background(
    job_id: str,
    ctx: PipelineContext,
    request: Request,
) -> None:
    """Background task: run the engine pipeline, update job state, and
    publish lifecycle events to the event store.

    Respects the concurrent-job semaphore and pipeline timeout configured
    in app.state.
    """

    job_mgr: Any = request.app.state.job_manager
    event_store: Any = request.app.state.event_store
    run_pipeline = request.app.state.run_pipeline
    semaphore: asyncio.Semaphore = request.app.state.job_semaphore
    timeout: int = request.app.state.pipeline_timeout

    async with semaphore:
        try:
            # Mark running
            await job_mgr.update_status(job_id, JobStatus.SCRAPING)

            # Run the engine pipeline with cancellation support and timeout
            engine_emitter = _JobProgressEmitter(job_mgr, event_store)
            coro = run_pipeline(
                ctx, engine_emitter,
                cancelled_check=lambda: job_mgr.is_cancelled(job_id),
            )

            if timeout > 0:
                try:
                    report_output = await asyncio.wait_for(coro, timeout=timeout)
                except asyncio.TimeoutError:
                    error_msg = f"Pipeline timed out after {timeout}s"
                    logger.error("%s for job %s", error_msg, job_id)
                    await job_mgr.set_error(job_id, error_msg)
                    await _emit(event_store, job_id, EventType.JOB_FAILED, error_msg)
                    return
            else:
                report_output = await coro

            # Check if the job was cancelled while running
            if job_mgr.is_cancelled(job_id):
                await _emit(event_store, job_id, EventType.JOB_CANCELLED, "Job cancelled during pipeline execution")
            elif ctx.state == PipelineState.ERROR:
                await job_mgr.set_error(job_id, report_output.executive_summary)
                await _emit(event_store, job_id, EventType.JOB_FAILED, report_output.executive_summary)
            else:
                # Convert ReportOutput to IntelligenceReport and save it
                if report_output is not None:
                    intel_report = _report_output_to_intelligence_report(
                        job_id, report_output, ctx.competitor_urls,
                        verification_passes=ctx.verification_passes,
                    )
                    await job_mgr.set_report(job_id, intel_report)

                # Mark completed
                await job_mgr.update_status(job_id, JobStatus.COMPLETED)
                await job_mgr.update_progress(job_id, progress=1.0, current_step="completed")
                await _emit(event_store, job_id, EventType.JOB_COMPLETED, "Job completed")
        except Exception as exc:
            logger.exception("Pipeline failed for job %s", job_id)
            # Sanitize: don't leak internal details to API consumers
            error_msg = f"Pipeline failed: {type(exc).__name__}"
            await job_mgr.set_error(job_id, error_msg)
            await _emit(event_store, job_id, EventType.JOB_FAILED, error_msg)
        finally:
            await event_store.close_job(job_id)


async def _emit(event_store: Any, job_id: str, event_type: EventType, message: str,
                data: dict[str, Any] | None = None) -> None:
    from datetime import datetime, timezone
    await event_store.publish(AgentEvent(
        event_id=f"{event_type.value}-{job_id}-{uuid.uuid4().hex[:8]}",
        event_type=event_type, job_id=job_id, agent_name="backend",
        timestamp=datetime.now(timezone.utc), message=message, data=data,
    ))


# ── Endpoints ─────────────────────────────────────────────────────────────


@router.post("/api/jobs", response_model=CreateJobResponse, status_code=201)
async def create_job(body: CreateJobRequest, request: Request) -> CreateJobResponse:
    """Create a new analysis job and kick off the pipeline in the background."""
    job_mgr = request.app.state.job_manager
    scheduler = request.app.state.scheduler

    job_id = uuid.uuid4().hex
    schedule_id: str | None = None
    if body.schedule and body.schedule.frequency.value != "once":
        schedule_id = f"schedule-{job_id}"
        database = getattr(request.app.state, "database", None)
        if database is None:
            raise HTTPException(status_code=500, detail="Schedule storage is unavailable")
        await database.create_schedule(
            schedule_id, job_id, body,
            body.schedule.frequency.value,
            body.schedule.cron_expression,
        )
        from backend.routes.schedules import _scheduled_callback

        if not scheduler.add_scheduled_job(job_id, body.schedule, _scheduled_callback, app=request.app):
            await database.delete_schedule(schedule_id)
            raise HTTPException(status_code=400, detail="Invalid schedule configuration")

    try:
        await job_mgr.create_job(job_id, body)
    except Exception:
        if schedule_id is not None:
            scheduler.remove_scheduled_job(job_id)
            database = getattr(request.app.state, "database", None)
            if database is not None:
                await database.delete_schedule(schedule_id)
        raise

    ctx = PipelineContext(
        job_id=job_id,
        query=body.query,
        competitor_urls=[c.url for c in body.competitors],
        focus_areas=_focus_areas_from_request(body),
        **_configured_pipeline_kwargs(),
    )

    # Fire-and-forget background task
    _start_background_task(request, _run_job_background(job_id, ctx, request))

    return CreateJobResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        message="Job created. Pipeline started.",
    )



@router.get("/api/jobs", response_model=JobListResponse)
async def list_jobs(request: Request) -> JobListResponse:
    """List all tracked jobs."""
    job_mgr = request.app.state.job_manager
    jobs = await job_mgr.list_jobs()
    return JobListResponse(jobs=jobs, total=len(jobs))


@router.get("/api/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job(job_id: str, request: Request) -> JobStatusResponse:
    """Get status of a single job."""
    job_mgr = request.app.state.job_manager
    record = await job_mgr.get_job(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return record.to_status_response()


@router.get("/api/jobs/{job_id}/stream")
async def stream_job(job_id: str, request: Request) -> EventSourceResponse:
    """SSE event stream for *job_id*.

    Supports ``Last-Event-Id`` header for reconnection replay.
    Sends heartbeat comments every 15 seconds.
    """
    job_mgr = request.app.state.job_manager
    event_store = request.app.state.event_store

    # Verify job exists
    record = await job_mgr.get_job(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Job not found")

    last_event_id: str | None = request.headers.get("last-event-id")

    async def event_generator():
        HEARTBEAT_INTERVAL = 15  # seconds

        async for event in event_store.subscribe(job_id, last_event_id=last_event_id):
            yield {
                "event": event.event_type.value,
                "id": event.event_id,
                "data": event.model_dump_json(),
            }

        # After the subscription ends, keep sending heartbeats until the
        # client disconnects or the job is known to be finished.
        record = await job_mgr.get_job(job_id)
        history = event_store.get_history(job_id)
        job_ended = (
            (record and record.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED))
            or (history and history[-1].event_type in (EventType.JOB_COMPLETED, EventType.JOB_FAILED, EventType.JOB_CANCELLED))
        )
        if not job_ended:
            while True:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                yield {"comment": "heartbeat"}

    return EventSourceResponse(event_generator())


@router.get("/api/jobs/{job_id}/report", response_model=ReportResponse)
async def get_report(job_id: str, request: Request) -> ReportResponse:
    """Retrieve the final report for a completed job."""
    job_mgr = request.app.state.job_manager
    record = await job_mgr.get_job(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if record.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Job is not yet completed")
    report = await job_mgr.get_report(job_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not available")
    return ReportResponse(report=report)


@router.delete("/api/jobs/{job_id}", response_model=CancelJobResponse)
async def cancel_job(job_id: str, request: Request) -> CancelJobResponse:
    """Cancel a running or pending job. Idempotent for already-cancelled jobs."""
    job_mgr = request.app.state.job_manager
    record = await job_mgr.get_job(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if record.status == JobStatus.CANCELLED:
        return CancelJobResponse(job_id=job_id, status=JobStatus.CANCELLED, message="Job cancelled")
    if record.status in (JobStatus.COMPLETED, JobStatus.FAILED):
        raise HTTPException(status_code=400, detail=f"Cannot cancel job in '{record.status.value}' state")

    await job_mgr.cancel_job(job_id)
    return CancelJobResponse(job_id=job_id, status=JobStatus.CANCELLED, message="Job cancelled")


@router.post("/api/jobs/{job_id}/export", response_model=ExportResponse)
async def export_report_endpoint(job_id: str, body: ExportRequest, request: Request) -> ExportResponse:
    """Export the report for a completed job in the requested format."""
    from backend.services.export import export_report

    job_mgr = request.app.state.job_manager
    record = await job_mgr.get_job(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if record.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Job is not yet completed")

    report = await job_mgr.get_report(job_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not available")

    return export_report(report, body, job_id)
