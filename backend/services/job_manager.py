"""Job state management backed by SQLite with cancellation support."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from contracts.api import (
    CreateJobRequest,
    IntelligenceReport,
    JobStatus,
    JobStatusResponse,
)

from .database import Database

logger = logging.getLogger(__name__)

class JobRecord:
    """Internal representation of a job — mutable fields that the
    pipeline updates as it runs."""

    def __init__(
        self,
        job_id: str,
        request: CreateJobRequest,
    ) -> None:
        self.job_id = job_id
        self.request = request
        self.status: JobStatus = JobStatus.PENDING
        self.progress: float = 0.0
        self.current_step: Optional[str] = None
        self.competitors_found: int = 0
        self.pages_scraped: int = 0
        self.findings_count: int = 0
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.error: Optional[str] = None
        self.report: Optional[IntelligenceReport] = None

    def to_status_response(self) -> JobStatusResponse:
        return JobStatusResponse(
            job_id=self.job_id,
            status=self.status,
            progress=self.progress,
            current_step=self.current_step,
            competitors_found=self.competitors_found,
            pages_scraped=self.pages_scraped,
            findings_count=self.findings_count,
            started_at=self.started_at,
            completed_at=self.completed_at,
            error=self.error,
        )

class JobManager:
    """Job store backed by SQLite with an in-memory cache for active jobs.

    All mutations are guarded by an ``asyncio.Lock`` so concurrent
    request handlers cannot corrupt state.
    """

    def __init__(self, database: Optional[Database] = None) -> None:
        self._db = database
        self._jobs: dict[str, JobRecord] = {}
        self._lock = asyncio.Lock()
        self._cancelled: set[str] = set()

    @property
    def _db_ready(self) -> bool:
        return self._db is not None

    async def initialize(self) -> None:
        if not self._db_ready:
            return
        loaded = 0
        for row in await self._db.list_jobs():
            try:
                req = CreateJobRequest.model_validate_json(row["request_json"])
                rec = JobRecord(job_id=row["id"], request=req)
                rec.status = JobStatus(row["status"])
                rec.progress = row["progress"]
                rec.current_step = row["current_step"]
                rec.competitors_found = row["competitors_found"]
                rec.pages_scraped = row["pages_scraped"]
                rec.findings_count = row["findings_count"]
                rec.started_at = datetime.fromisoformat(row["started_at"]) if row["started_at"] else None
                rec.completed_at = datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None
                rec.error = row["error"]
                if row["report_json"]:
                    try:
                        rec.report = IntelligenceReport.model_validate_json(row["report_json"])
                    except Exception as exc:
                        logger.debug("Skipping invalid saved report for job %s: %s", row["id"], exc)
                self._jobs[row["id"]] = rec
                loaded += 1
            except Exception as exc:
                logger.warning("Skipping corrupted job row %s: %s", row.get("id", "?"), exc)
        logger.info("Loaded %d jobs from database", loaded)

    async def create_job(self, job_id: str, request: CreateJobRequest) -> JobRecord:
        async with self._lock:
            record = JobRecord(job_id=job_id, request=request)
            record.competitors_found = len(request.competitors)
            self._jobs[job_id] = record
            if self._db_ready:
                await self._db.create_job(job_id, request)
            return record

    async def get_job(self, job_id: str) -> Optional[JobRecord]:
        async with self._lock:
            return self._jobs.get(job_id)

    async def list_jobs(self) -> list[JobStatusResponse]:
        async with self._lock:
            return [r.to_status_response() for r in self._jobs.values()]

    async def list_records(self) -> list[JobRecord]:
        """Return raw JobRecord objects (for internal use by analytics)."""
        async with self._lock:
            return list(self._jobs.values())

    async def update_status(self, job_id: str, status: JobStatus) -> None:
        async with self._lock:
            rec = self._jobs.get(job_id)
            if rec is None:
                return
            rec.status = status
            if status == JobStatus.SCRAPING and rec.started_at is None:
                rec.started_at = datetime.now(timezone.utc)
            if status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                rec.completed_at = datetime.now(timezone.utc)
                self._cancelled.discard(job_id)  # clean up cancellation set
            if self._db_ready:
                updates: dict = {"status": status}
                if rec.started_at and status == JobStatus.SCRAPING:
                    updates["started_at"] = rec.started_at
                if rec.completed_at and status in (
                    JobStatus.COMPLETED,
                    JobStatus.FAILED,
                    JobStatus.CANCELLED,
                ):
                    updates["completed_at"] = rec.completed_at
                await self._db.update_job(job_id, **updates)

    async def update_progress(
        self,
        job_id: str,
        *,
        progress: Optional[float] = None,
        current_step: Optional[str] = None,
        pages_scraped: Optional[int] = None,
        findings_count: Optional[int] = None,
        competitors_found: Optional[int] = None,
    ) -> None:
        async with self._lock:
            rec = self._jobs.get(job_id)
            if rec is None:
                return
            updates: dict = {}
            if progress is not None:
                rec.progress = min(max(progress, 0.0), 1.0)
                updates["progress"] = rec.progress
            for field, value in [("current_step", current_step), ("pages_scraped", pages_scraped),
                                 ("findings_count", findings_count), ("competitors_found", competitors_found)]:
                if value is not None:
                    setattr(rec, field, value)
                    updates[field] = value
            if self._db_ready and updates:
                await self._db.update_job(job_id, **updates)

    async def set_error(self, job_id: str, error: str) -> None:
        async with self._lock:
            rec = self._jobs.get(job_id)
            if rec is None:
                return
            rec.error = error
            rec.status = JobStatus.FAILED
            rec.completed_at = datetime.now(timezone.utc)
            if self._db_ready:
                await self._db.update_job(
                    job_id,
                    error=error,
                    status=JobStatus.FAILED,
                    completed_at=rec.completed_at,
                )

    async def set_report(self, job_id: str, report: IntelligenceReport) -> None:
        async with self._lock:
            rec = self._jobs.get(job_id)
            if rec is None:
                return
            rec.report = report
            if self._db_ready:
                await self._db.save_report(job_id, report)

    async def get_report(self, job_id: str) -> Optional[IntelligenceReport]:
        async with self._lock:
            rec = self._jobs.get(job_id)
            if rec and rec.report:
                return rec.report
            # Fallback to DB for reports loaded after restart
            if self._db_ready:
                return await self._db.get_report(job_id)
            return None

    def is_cancelled(self, job_id: str) -> bool:
        """Check if a job has been cancelled (no lock needed for set read)."""
        return job_id in self._cancelled

    async def cancel_job(self, job_id: str) -> bool:
        """Mark a job as cancelled. Returns True if the job existed."""
        async with self._lock:
            rec = self._jobs.get(job_id)
            if rec is None:
                return False
            if rec.status not in (
                JobStatus.COMPLETED,
                JobStatus.FAILED,
                JobStatus.CANCELLED,
            ):
                self._cancelled.add(job_id)
                rec.status = JobStatus.CANCELLED
                rec.completed_at = datetime.now(timezone.utc)
                if self._db_ready:
                    await self._db.update_job(
                        job_id,
                        status=JobStatus.CANCELLED,
                        completed_at=rec.completed_at,
                    )
            return True
