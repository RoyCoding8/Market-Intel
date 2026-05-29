"""SQLite persistence layer using aiosqlite."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import aiosqlite

from contracts.api import (
    CreateJobRequest,
    DashboardStats,
    IntelligenceReport,
    JobStatus,
    TrendDataPoint,
)

logger = logging.getLogger(__name__)

DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'pending',
    progress REAL NOT NULL DEFAULT 0.0,
    current_step TEXT,
    competitors_found INTEGER NOT NULL DEFAULT 0,
    pages_scraped INTEGER NOT NULL DEFAULT 0,
    findings_count INTEGER NOT NULL DEFAULT 0,
    started_at TEXT,
    completed_at TEXT,
    error TEXT,
    report_json TEXT,
    request_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    message TEXT NOT NULL,
    data_json TEXT,
    sequence INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS schedules (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    request_json TEXT NOT NULL,
    frequency TEXT NOT NULL,
    cron_expression TEXT,
    next_run TEXT,
    last_run TEXT,
    last_job_id TEXT,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_job_id ON events(job_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at);
"""


class Database:
    """Async SQLite database for persisting jobs, events, and schedules."""

    def __init__(self, db_path: str = "./data/market_intel.db") -> None:
        self.db_path = db_path
        self._db: Optional[aiosqlite.Connection] = None
        self._init_lock = asyncio.Lock()
        self._seq_lock = asyncio.Lock()
        self._sequence: int = 0

    async def initialize(self) -> None:
        """Create tables and open connection."""
        if self._db is not None:
            return
        async with self._init_lock:
            if self._db is not None:
                return
            os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
            self._db = await aiosqlite.connect(self.db_path, timeout=30)
            self._db.row_factory = aiosqlite.Row
            await self._db.execute("PRAGMA journal_mode=WAL")
            await self._db.execute("PRAGMA busy_timeout=30000")
            await self._db.executescript(DB_SCHEMA)
            await self._db.commit()

            async with self._db.execute(
                "SELECT COALESCE(MAX(sequence), 0) FROM events"
            ) as cursor:
                row = await cursor.fetchone()
                self._sequence = row[0]

    async def close(self) -> None:
        """Close the database connection."""
        if self._db:
            await self._db.close()
            self._db = None

    @property
    def connected(self) -> bool:
        return self._db is not None

    async def _connection(self) -> aiosqlite.Connection:
        await self.initialize()
        if self._db is None:  # pragma: no cover - defensive guard
            raise RuntimeError("Database failed to initialize")
        return self._db


    async def create_job(self, job_id: str, request: CreateJobRequest) -> None:
        db = await self._connection()
        now = datetime.now(timezone.utc).isoformat()
        request_json = request.model_dump_json()
        await db.execute(
            "INSERT INTO jobs (id, status, competitors_found, request_json, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (job_id, JobStatus.PENDING.value, len(request.competitors), request_json, now),
        )
        await db.commit()

    async def get_job(self, job_id: str) -> Optional[dict]:
        db = await self._connection()
        async with db.execute(
            "SELECT * FROM jobs WHERE id = ?", (job_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def list_jobs(self) -> list[dict]:
        db = await self._connection()
        async with db.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    _JOB_COLUMNS = frozenset({
        "status", "progress", "current_step", "competitors_found",
        "pages_scraped", "findings_count", "report_json", "error",
        "started_at", "completed_at",
    })

    async def update_job(self, job_id: str, **kwargs) -> None:
        """Update job columns. Only columns in _JOB_COLUMNS are accepted."""
        filtered = {k: v for k, v in kwargs.items() if k in self._JOB_COLUMNS}
        if not filtered:
            return
        db = await self._connection()
        for key, value in list(filtered.items()):
            if isinstance(value, datetime):
                filtered[key] = value.isoformat()
            elif isinstance(value, JobStatus):
                filtered[key] = value.value
        set_clause = ", ".join(f"{k} = ?" for k in filtered)
        values = list(filtered.values()) + [job_id]
        await db.execute(
            f"UPDATE jobs SET {set_clause} WHERE id = ?", values
        )
        await db.commit()

    async def save_report(self, job_id: str, report: IntelligenceReport) -> None:
        db = await self._connection()
        await db.execute(
            "UPDATE jobs SET report_json = ? WHERE id = ?",
            (report.model_dump_json(), job_id),
        )
        await db.commit()

    async def get_report(self, job_id: str) -> Optional[IntelligenceReport]:
        db = await self._connection()
        async with db.execute(
            "SELECT report_json FROM jobs WHERE id = ?", (job_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row is None or row[0] is None:
                return None
            try:
                return IntelligenceReport.model_validate_json(row[0])
            except Exception as exc:
                logger.warning("Corrupted report_json for job %s: %s", job_id, exc)
                return None


    async def save_event(
        self,
        job_id: str,
        event_type: str,
        agent_name: str,
        message: str,
        data: Optional[dict] = None,
    ) -> int:
        db = await self._connection()
        async with self._seq_lock:
            self._sequence += 1
            seq = self._sequence
        now = datetime.now(timezone.utc).isoformat()
        data_json = json.dumps(data) if data else None
        await db.execute(
            "INSERT INTO events (job_id, event_type, agent_name, timestamp, "
            "message, data_json, sequence) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (job_id, event_type, agent_name, now, message, data_json, seq),
        )
        await db.commit()
        return seq

    async def get_events(self, job_id: str) -> list[dict]:
        db = await self._connection()
        async with db.execute(
            "SELECT * FROM events WHERE job_id = ? ORDER BY sequence", (job_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


    async def get_dashboard_stats(self) -> DashboardStats:
        db = await self._connection()
        completed = JobStatus.COMPLETED.value

        async def _scalar(sql: str, params: tuple = ()) -> int:
            async with db.execute(sql, params) as cur:
                row = await cur.fetchone()
                return row[0] if row else 0

        total_jobs = await _scalar("SELECT COUNT(*) FROM jobs")
        completed_jobs = await _scalar("SELECT COUNT(*) FROM jobs WHERE status = ?", (completed,))
        failed_jobs = await _scalar("SELECT COUNT(*) FROM jobs WHERE status = ?", (JobStatus.FAILED.value,))

        async with db.execute(
            "SELECT COALESCE(SUM(findings_count), 0), COALESCE(SUM(pages_scraped), 0) "
            "FROM jobs WHERE status = ?", (completed,),
        ) as cur:
            row = await cur.fetchone()
            total_findings, total_pages_scraped = row[0], row[1]

        high_confidence = total_verifications = 0
        total_confidence = 0.0
        confidence_count = 0
        findings_by_category: dict[str, int] = {}
        async with db.execute("SELECT report_json FROM jobs WHERE report_json IS NOT NULL") as cur:
            async for row in cur:
                try:
                    report = IntelligenceReport.model_validate_json(row[0])
                    total_verifications += report.verification_passes
                    for f in report.findings:
                        if f.confidence_score >= 0.8:
                            high_confidence += 1
                        total_confidence += f.confidence_score
                        confidence_count += 1
                        findings_by_category[f.category] = findings_by_category.get(f.category, 0) + 1
                except Exception as exc:
                    logger.debug("Skipping invalid report_json while building dashboard stats: %s", exc)

        seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        jobs_last_7_days = await _scalar("SELECT COUNT(*) FROM jobs WHERE created_at >= ?", (seven_days_ago,))

        competitor_map: dict[str, dict] = {}
        async with db.execute("SELECT request_json FROM jobs") as cur:
            async for row in cur:
                try:
                    req = CreateJobRequest.model_validate_json(row[0])
                    for c in req.competitors:
                        if c.url not in competitor_map:
                            competitor_map[c.url] = {"name": c.name or c.url, "url": c.url, "job_count": 0}
                        competitor_map[c.url]["job_count"] += 1
                except Exception as exc:
                    logger.debug("Skipping invalid request_json while building competitor stats: %s", exc)

        return DashboardStats(
            total_jobs=total_jobs, completed_jobs=completed_jobs, failed_jobs=failed_jobs,
            total_findings=total_findings, high_confidence_findings=high_confidence,
            total_competitors_tracked=len(competitor_map), total_pages_scraped=total_pages_scraped,
            total_verifications=total_verifications,
            average_confidence_score=total_confidence / confidence_count if confidence_count else 0.0,
            jobs_last_7_days=jobs_last_7_days, findings_by_category=findings_by_category,
            top_competitors=sorted(competitor_map.values(), key=lambda x: x["job_count"], reverse=True)[:10],
        )

    async def get_trend_data(self, metric: str, days: int) -> list[TrendDataPoint]:
        start = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        db = await self._connection()

        if metric == "jobs_created":
            sql = "SELECT DATE(created_at) AS d, COUNT(*) FROM jobs WHERE created_at >= ? GROUP BY d ORDER BY d"
            params = (start,)
        elif metric == "findings_count":
            sql = ("SELECT DATE(completed_at) AS d, SUM(findings_count) FROM jobs "
                   "WHERE status = ? AND completed_at >= ? GROUP BY d ORDER BY d")
            params = (JobStatus.COMPLETED.value, start)
        elif metric == "pages_scraped":
            sql = ("SELECT DATE(completed_at) AS d, SUM(pages_scraped) FROM jobs "
                   "WHERE status = ? AND completed_at >= ? GROUP BY d ORDER BY d")
            params = (JobStatus.COMPLETED.value, start)
        elif metric == "confidence_score":
            daily: dict[str, list[float]] = {}
            async with db.execute(
                "SELECT DATE(completed_at) AS d, report_json FROM jobs "
                "WHERE status = ? AND completed_at >= ? AND report_json IS NOT NULL",
                (JobStatus.COMPLETED.value, start),
            ) as cur:
                async for row in cur:
                    try:
                        for f in IntelligenceReport.model_validate_json(row[1]).findings:
                            daily.setdefault(row[0], []).append(f.confidence_score)
                    except Exception as exc:
                        logger.debug("Skipping invalid report_json while building trend data: %s", exc)
            return [TrendDataPoint(date=d, value=sum(s) / len(s)) for d, s in sorted(daily.items())]
        else:
            return []

        async with db.execute(sql, params) as cur:
            return [TrendDataPoint(date=r[0], value=float(r[1] or 0)) async for r in cur]


    async def create_schedule(
        self,
        schedule_id: str,
        job_id: str,
        request: CreateJobRequest,
        frequency: str,
        cron_expression: Optional[str] = None,
    ) -> None:
        db = await self._connection()
        now = datetime.now(timezone.utc).isoformat()
        await db.execute(
            "INSERT INTO schedules (id, job_id, request_json, frequency, "
            "cron_expression, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (schedule_id, job_id, request.model_dump_json(), frequency, cron_expression, now),
        )
        await db.commit()

    async def get_schedule(self, schedule_id: str) -> Optional[dict]:
        db = await self._connection()
        async with db.execute(
            "SELECT * FROM schedules WHERE id = ?", (schedule_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

    async def list_schedules(self) -> list[dict]:
        db = await self._connection()
        async with db.execute(
            "SELECT * FROM schedules ORDER BY created_at DESC"
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]

    _SCHEDULE_COLUMNS = frozenset({
        "frequency", "cron_expression", "enabled", "last_run", "last_job_id", "request_json",
    })

    async def update_schedule(self, schedule_id: str, **kwargs) -> None:
        filtered = {k: v for k, v in kwargs.items() if k in self._SCHEDULE_COLUMNS}
        if not filtered:
            return
        db = await self._connection()
        for key, value in list(filtered.items()):
            if isinstance(value, datetime):
                filtered[key] = value.isoformat()
            elif isinstance(value, JobStatus):
                filtered[key] = value.value
            elif key == "enabled":
                filtered[key] = 1 if value else 0
        set_clause = ", ".join(f"{k} = ?" for k in filtered)
        vals = list(filtered.values()) + [schedule_id]
        await db.execute(
            f"UPDATE schedules SET {set_clause} WHERE id = ?", vals
        )
        await db.commit()

    async def delete_schedule(self, schedule_id: str) -> bool:
        db = await self._connection()
        async with db.execute(
            "DELETE FROM schedules WHERE id = ?", (schedule_id,)
        ) as cur:
            await db.commit()
            return cur.rowcount > 0

    async def get_schedule_by_job_id(self, job_id: str) -> Optional[dict]:
        db = await self._connection()
        async with db.execute(
            "SELECT * FROM schedules WHERE job_id = ?", (job_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None
