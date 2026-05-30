"""Scheduled job endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from contracts.api import (
    CreateJobRequest,
    ScheduleConfig,
    ScheduledJobListResponse,
    ScheduledJobResponse,
    ScheduleFrequency,
    UpdateScheduleRequest,
)

router = APIRouter(tags=["schedules"])

def _schedule_response(row: dict, live_schedule: dict | None = None) -> ScheduledJobResponse:
    return ScheduledJobResponse(
        schedule_id=row["id"],
        job_config=CreateJobRequest.model_validate_json(row["request_json"]),
        frequency=ScheduleFrequency(row["frequency"]),
        cron_expression=row["cron_expression"],
        next_run=(live_schedule or {}).get("next_run") or row.get("next_run"),
        last_run=row.get("last_run"),
        last_job_id=row.get("last_job_id"),
        enabled=bool(row["enabled"]),
        created_at=row["created_at"],
    )

@router.get("/api/schedules", response_model=ScheduledJobListResponse)
async def list_schedules(request: Request) -> ScheduledJobListResponse:
    """List all scheduled jobs."""
    database: Any = request.app.state.database
    scheduler: Any = request.app.state.scheduler
    live_by_job_id = {item["job_id"]: item for item in scheduler.list_scheduled_jobs()}
    schedules = [
        _schedule_response(row, live_by_job_id.get(row["job_id"]))
        for row in await database.list_schedules()
    ]
    return ScheduledJobListResponse(schedules=schedules, total=len(schedules))

@router.post("/api/schedules", response_model=ScheduledJobResponse, status_code=201)
async def create_schedule(body: CreateJobRequest, request: Request) -> ScheduledJobResponse:
    """Create a new scheduled job."""
    if body.schedule is None:
        raise HTTPException(status_code=400, detail="Schedule configuration required")
    if body.schedule.frequency.value == "once":
        raise HTTPException(status_code=400, detail="Use /api/jobs for one-time analyses")

    database: Any = request.app.state.database
    scheduler: Any = request.app.state.scheduler

    job_id = uuid.uuid4().hex
    schedule_id = f"schedule-{job_id}"
    await database.create_schedule(
        schedule_id,
        job_id,
        body,
        body.schedule.frequency.value,
        body.schedule.cron_expression,
    )
    if not scheduler.add_scheduled_job(job_id, body.schedule, _scheduled_callback, app=request.app):
        await database.delete_schedule(schedule_id)
        raise HTTPException(status_code=400, detail="Invalid schedule configuration")

    return ScheduledJobResponse(
        schedule_id=schedule_id,
        job_config=body,
        frequency=body.schedule.frequency,
        cron_expression=body.schedule.cron_expression,
        next_run=body.schedule.next_run,
        last_run=None,
        last_job_id=None,
        enabled=True,
        created_at=datetime.now(timezone.utc),
    )

@router.patch("/api/schedules/{schedule_id}", response_model=ScheduledJobResponse)
async def update_schedule(
    schedule_id: str,
    body: UpdateScheduleRequest,
    request: Request,
) -> ScheduledJobResponse:
    """Update a schedule (enable/disable)."""
    database: Any = request.app.state.database
    scheduler: Any = request.app.state.scheduler
    row = await database.get_schedule(schedule_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Schedule not found")

    job_id = row["job_id"]
    updates: dict[str, Any] = {}
    if body.frequency is not None:
        if body.frequency == ScheduleFrequency.ONCE:
            raise HTTPException(status_code=400, detail="Use /api/jobs for one-time analyses")
        updates["frequency"] = body.frequency.value
    if body.cron_expression is not None:
        updates["cron_expression"] = body.cron_expression
    if body.enabled is not None:
        updates["enabled"] = body.enabled

    next_enabled = body.enabled if body.enabled is not None else bool(row["enabled"])
    next_frequency = body.frequency.value if body.frequency is not None else row["frequency"]
    next_cron = body.cron_expression if body.cron_expression is not None else row["cron_expression"]

    if next_enabled and (
        body.enabled is True or body.frequency is not None or body.cron_expression is not None
    ):
        schedule = ScheduleConfig(
            frequency=ScheduleFrequency(next_frequency),
            cron_expression=next_cron,
        )
        if not scheduler.add_scheduled_job(job_id, schedule, _scheduled_callback, app=request.app):
            raise HTTPException(status_code=400, detail="Invalid schedule configuration")

    if updates:
        await database.update_schedule(schedule_id, **updates)
        row = await database.get_schedule(schedule_id)

    if body.enabled is False:
        scheduler.remove_scheduled_job(job_id, keep_metadata=True)

    live_by_job_id = {item["job_id"]: item for item in scheduler.list_scheduled_jobs()}
    return _schedule_response(row, live_by_job_id.get(job_id))

@router.delete("/api/schedules/{schedule_id}")
async def delete_schedule(schedule_id: str, request: Request) -> dict[str, str]:
    """Delete a scheduled job."""
    database: Any = request.app.state.database
    scheduler: Any = request.app.state.scheduler
    row = await database.get_schedule(schedule_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    scheduler.remove_scheduled_job(row["job_id"])
    await database.delete_schedule(schedule_id)
    return {"status": "deleted", "schedule_id": schedule_id}

async def _scheduled_callback(job_id: str, request: Request | None = None, app: Any = None) -> None:
    """Callback invoked by APScheduler for recurring jobs."""
    from contracts.engine import PipelineContext
    from backend.routes.jobs import (
        _configured_pipeline_kwargs,
        _focus_areas_from_request,
        _run_job_background,
        _start_background_task,
    )

    application = app or (request.app if request is not None else None)
    if application is None:
        return

    database: Any = application.state.database
    job_mgr: Any = application.state.job_manager
    row = await database.get_schedule_by_job_id(job_id)
    if row is None:
        return
    req = CreateJobRequest.model_validate_json(row["request_json"])

    new_id = uuid.uuid4().hex
    await job_mgr.create_job(new_id, req)
    ctx = PipelineContext(
        job_id=new_id, query=req.query,
        competitor_urls=[c.url for c in req.competitors],
        focus_areas=_focus_areas_from_request(req),
        **_configured_pipeline_kwargs(),
    )
    await database.update_schedule(
        row["id"],
        last_run=datetime.now(timezone.utc),
        last_job_id=new_id,
    )
    task_request = request or _AppRequest(application)
    _start_background_task(task_request, _run_job_background(new_id, ctx, task_request))

class _AppRequest:
    def __init__(self, app: Any) -> None:
        self.app = app
