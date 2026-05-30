"""Tests for the scheduler service."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from contracts.api import ScheduleConfig, ScheduleFrequency
from backend.services.scheduler import SchedulerService

@pytest_asyncio.fixture
async def scheduler() -> SchedulerService:
    svc = SchedulerService()
    svc.start()
    yield svc
    svc.shutdown(wait=False)

@pytest.mark.asyncio
async def test_scheduler_starts(scheduler: SchedulerService):
    assert scheduler.running is True

@pytest.mark.asyncio
async def test_scheduler_lists_jobs(scheduler: SchedulerService):
    cb = AsyncMock()
    schedule = ScheduleConfig(frequency=ScheduleFrequency.HOURLY)
    scheduler.add_scheduled_job("j1", schedule, cb)
    jobs = scheduler.list_scheduled_jobs()
    assert len(jobs) == 1
    assert jobs[0]["id"] == "schedule-j1"

@pytest.mark.asyncio
async def test_remove_scheduled_job(scheduler: SchedulerService):
    cb = AsyncMock()
    schedule = ScheduleConfig(frequency=ScheduleFrequency.DAILY)
    scheduler.add_scheduled_job("j2", schedule, cb)
    scheduler.remove_scheduled_job("j2")
    assert scheduler.list_scheduled_jobs() == []

@pytest.mark.asyncio
async def test_once_frequency_not_scheduled(scheduler: SchedulerService):
    cb = AsyncMock()
    schedule = ScheduleConfig(frequency=ScheduleFrequency.ONCE)
    scheduler.add_scheduled_job("j3", schedule, cb)
    # ONCE maps to None trigger, so nothing is added
    assert scheduler.list_scheduled_jobs() == []

@pytest.mark.asyncio
async def test_custom_cron(scheduler: SchedulerService):
    cb = AsyncMock()
    schedule = ScheduleConfig(
        frequency=ScheduleFrequency.CUSTOM,
        cron_expression="*/5 * * * *",
    )
    scheduler.add_scheduled_job("j4", schedule, cb)
    jobs = scheduler.list_scheduled_jobs()
    assert len(jobs) == 1
    assert "every 5" in jobs[0]["trigger"].lower() or "cron" in jobs[0]["trigger"].lower()

@pytest.mark.asyncio
async def test_shutdown():
    svc = SchedulerService()
    svc.start()
    assert svc.running is True
    svc.shutdown()
    assert svc.running is False
