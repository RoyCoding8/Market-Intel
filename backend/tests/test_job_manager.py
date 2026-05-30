"""Tests for the job manager service."""

from __future__ import annotations

import pytest

from contracts.api import (
    CompetitorInput,
    CreateJobRequest,
    IntelligenceReport,
    JobStatus,
)
from backend.services.job_manager import JobManager

def _make_request() -> CreateJobRequest:
    return CreateJobRequest(
        competitors=[CompetitorInput(url="https://example.com")],
    )

@pytest.mark.asyncio
async def test_create_and_get(job_manager: JobManager):
    rec = await job_manager.create_job("j1", _make_request())
    assert rec.job_id == "j1"
    assert rec.status == JobStatus.PENDING

    fetched = await job_manager.get_job("j1")
    assert fetched is not None
    assert fetched.job_id == "j1"

@pytest.mark.asyncio
async def test_get_nonexistent(job_manager: JobManager):
    assert await job_manager.get_job("nope") is None

@pytest.mark.asyncio
async def test_list_jobs(job_manager: JobManager):
    await job_manager.create_job("a", _make_request())
    await job_manager.create_job("b", _make_request())
    jobs = await job_manager.list_jobs()
    ids = {j.job_id for j in jobs}
    assert ids == {"a", "b"}

@pytest.mark.asyncio
async def test_update_status_sets_started_at(job_manager: JobManager):
    await job_manager.create_job("j2", _make_request())
    await job_manager.update_status("j2", JobStatus.SCRAPING)
    rec = await job_manager.get_job("j2")
    assert rec is not None
    assert rec.status == JobStatus.SCRAPING
    assert rec.started_at is not None

@pytest.mark.asyncio
async def test_update_status_sets_completed_at(job_manager: JobManager):
    await job_manager.create_job("j3", _make_request())
    await job_manager.update_status("j3", JobStatus.SCRAPING)
    await job_manager.update_status("j3", JobStatus.COMPLETED)
    rec = await job_manager.get_job("j3")
    assert rec is not None
    assert rec.completed_at is not None

@pytest.mark.asyncio
async def test_update_progress(job_manager: JobManager):
    await job_manager.create_job("j4", _make_request())
    await job_manager.update_progress(
        "j4", progress=0.5, current_step="analyzing", pages_scraped=10, findings_count=3
    )
    rec = await job_manager.get_job("j4")
    assert rec is not None
    assert rec.progress == 0.5
    assert rec.current_step == "analyzing"
    assert rec.pages_scraped == 10
    assert rec.findings_count == 3

@pytest.mark.asyncio
async def test_update_progress_clamps(job_manager: JobManager):
    await job_manager.create_job("j5", _make_request())
    await job_manager.update_progress("j5", progress=1.5)
    rec = await job_manager.get_job("j5")
    assert rec is not None
    assert rec.progress == 1.0

    await job_manager.update_progress("j5", progress=-0.5)
    rec = await job_manager.get_job("j5")
    assert rec is not None
    assert rec.progress == 0.0

@pytest.mark.asyncio
async def test_set_error(job_manager: JobManager):
    await job_manager.create_job("j6", _make_request())
    await job_manager.set_error("j6", "boom")
    rec = await job_manager.get_job("j6")
    assert rec is not None
    assert rec.status == JobStatus.FAILED
    assert rec.error == "boom"
    assert rec.completed_at is not None

@pytest.mark.asyncio
async def test_set_and_get_report(job_manager: JobManager):
    await job_manager.create_job("j7", _make_request())
    report = IntelligenceReport(
        id="r1",
        title="Test Report",
        created_at="2025-01-01T00:00:00Z",
        competitors=[],
        findings=[],
        executive_summary="All good",
    )
    await job_manager.set_report("j7", report)
    fetched = await job_manager.get_report("j7")
    assert fetched is not None
    assert fetched.id == "r1"

@pytest.mark.asyncio
async def test_get_report_none_when_not_set(job_manager: JobManager):
    await job_manager.create_job("j8", _make_request())
    assert await job_manager.get_report("j8") is None

@pytest.mark.asyncio
async def test_update_nonexistent_job_is_noop(job_manager: JobManager):
    # Should not raise
    await job_manager.update_status("ghost", JobStatus.SCRAPING)
    await job_manager.update_progress("ghost", progress=0.5)
    await job_manager.set_error("ghost", "err")
    await job_manager.set_report("ghost", IntelligenceReport(
        id="x", title="x", created_at="2025-01-01T00:00:00Z",
        competitors=[], findings=[], executive_summary="x",
    ))
