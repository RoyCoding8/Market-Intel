"""APScheduler integration for recurring jobs."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from contracts.api import ScheduleConfig, ScheduleFrequency

logger = logging.getLogger(__name__)

_FREQUENCY_CRON: dict[ScheduleFrequency, dict[str, str]] = {
    ScheduleFrequency.HOURLY: {"minute": "0"},
    ScheduleFrequency.DAILY: {"hour": "9", "minute": "0"},
    ScheduleFrequency.WEEKLY: {"day_of_week": "mon", "hour": "9", "minute": "0"},
}

RunJobCallback = Callable[..., Coroutine[Any, Any, None]]


class SchedulerService:
    """Thin wrapper around APScheduler for recurring market-intel jobs."""

    def __init__(self) -> None:
        self._scheduler = AsyncIOScheduler()
        self._started = False
        self._schedules: dict[str, dict[str, Any]] = {}

    @property
    def running(self) -> bool:
        return self._started

    def start(self) -> None:
        if not self._started:
            self._scheduler.start()
            self._started = True
            logger.info("APScheduler started")

    def shutdown(self, wait: bool = True) -> None:
        if self._started:
            self._scheduler.shutdown(wait=wait)
            self._started = False
            logger.info("APScheduler shut down")

    def add_scheduled_job(
        self, job_id: str, schedule: ScheduleConfig, callback: RunJobCallback, **kwargs: Any,
    ) -> bool:
        trigger = self._build_trigger(schedule)
        if trigger is None:
            logger.warning("Cannot schedule job %s: unsupported frequency", job_id)
            return False
        self._scheduler.add_job(
            callback, trigger=trigger, id=f"schedule-{job_id}",
            replace_existing=True, kwargs={"job_id": job_id, **kwargs},
        )
        self._schedules[job_id] = {
            "schedule_id": f"schedule-{job_id}",
            "job_id": job_id,
            "frequency": schedule.frequency,
            "cron_expression": schedule.cron_expression,
            "enabled": True,
            "created_at": datetime.now(timezone.utc),
        }
        logger.info("Scheduled job %s with %s", job_id, schedule.frequency.value)
        return True

    def remove_scheduled_job(self, job_id: str, *, keep_metadata: bool = False) -> None:
        sched_id = f"schedule-{job_id}"
        try:
            self._scheduler.remove_job(sched_id)
            logger.info("Removed scheduled job %s", job_id)
        except Exception:
            logger.debug("Scheduled job %s not found (already removed?)", job_id)
        if keep_metadata and job_id in self._schedules:
            self._schedules[job_id]["enabled"] = False
        else:
            self._schedules.pop(job_id, None)

    def list_scheduled_jobs(self) -> list[dict[str, Any]]:
        """Return a summary of every scheduled APScheduler job."""
        jobs_by_id = {job.id: job for job in self._scheduler.get_jobs()}
        summaries: list[dict[str, Any]] = []
        for job_id, meta in self._schedules.items():
            sched_id = f"schedule-{job_id}"
            job = jobs_by_id.get(sched_id)
            summaries.append({
                **meta,
                "id": sched_id,
                "next_run": job.next_run_time if job and job.next_run_time else None,
                "next_run_time": str(job.next_run_time) if job and job.next_run_time else None,
                "trigger": str(job.trigger) if job else None,
            })
        return summaries

    @staticmethod
    def _build_trigger(schedule: ScheduleConfig) -> Optional[CronTrigger]:
        if schedule.frequency == ScheduleFrequency.ONCE:
            return None  # one-shot jobs run through /api/jobs, not APScheduler

        if schedule.frequency == ScheduleFrequency.CUSTOM:
            if not schedule.cron_expression:
                logger.error("CUSTOM frequency requires cron_expression")
                return None
            try:
                trigger = CronTrigger.from_crontab(schedule.cron_expression)
            except ValueError as exc:
                logger.error("Invalid custom cron expression %r: %s", schedule.cron_expression, exc)
                return None
            fields = schedule.cron_expression.split()
            if len(fields) >= 2 and fields[0] != "*" and fields[1] != "*":
                pass  # Specific minute and hour — likely fine
            elif fields[0] == "*" and (len(fields) < 2 or fields[1] == "*"):
                logger.warning("Cron expression %r runs every minute — rejecting as too frequent", schedule.cron_expression)
                return None
            return trigger

        cron_kwargs = _FREQUENCY_CRON.get(schedule.frequency)
        if cron_kwargs is None:
            return None
        return CronTrigger(**cron_kwargs)
