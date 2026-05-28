"""Dashboard stats and trend data endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Query, Request

from contracts.api import DashboardStats, TrendDataPoint, TrendResponse

router = APIRouter(tags=["analytics"])


@router.get("/api/stats", response_model=DashboardStats)
async def get_stats(request: Request) -> DashboardStats:
    """Return aggregate dashboard statistics."""
    job_mgr: Any = request.app.state.job_manager
    records = await job_mgr.list_records()

    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    total_findings = high_confidence = total_verifications = 0
    total_confidence = 0.0
    confidence_count = total_pages_scraped = 0
    findings_by_category: dict[str, int] = {}
    competitor_map: dict[str, dict] = {}

    for rec in records:
        total_pages_scraped += rec.pages_scraped
        if rec.request:
            for c in rec.request.competitors:
                if c.url not in competitor_map:
                    competitor_map[c.url] = {"name": c.name or c.url, "url": c.url, "job_count": 0}
                competitor_map[c.url]["job_count"] += 1
        if rec.status.value == "completed" and rec.report:
            total_verifications += rec.report.verification_passes
            for f in rec.report.findings:
                total_findings += 1
                if f.confidence_score >= 0.8:
                    high_confidence += 1
                total_confidence += f.confidence_score
                confidence_count += 1
                findings_by_category[f.category] = findings_by_category.get(f.category, 0) + 1

    return DashboardStats(
        total_jobs=len(records),
        completed_jobs=sum(1 for r in records if r.status.value == "completed"),
        failed_jobs=sum(1 for r in records if r.status.value == "failed"),
        total_findings=total_findings, high_confidence_findings=high_confidence,
        total_competitors_tracked=len(competitor_map), total_pages_scraped=total_pages_scraped,
        total_verifications=total_verifications,
        average_confidence_score=total_confidence / confidence_count if confidence_count else 0.0,
        jobs_last_7_days=sum(1 for r in records if r.started_at and r.started_at >= week_ago),
        findings_by_category=findings_by_category,
        top_competitors=sorted(competitor_map.values(), key=lambda x: x["job_count"], reverse=True)[:10],
    )


@router.get("/api/trends", response_model=TrendResponse)
async def get_trends(
    request: Request,
    metric: str = Query("findings", description="Metric name"),
    days: int = Query(30, ge=1, le=365, description="Number of days"),
) -> TrendResponse:
    """Return trend data for charts."""
    job_mgr: Any = request.app.state.job_manager
    jobs = await job_mgr.list_jobs()
    start = datetime.now(timezone.utc) - timedelta(days=days)
    date_buckets: dict[str, float] = {}

    for job in jobs:
        if not (job.completed_at and job.completed_at >= start):
            continue
        key = job.completed_at.strftime("%Y-%m-%d")
        if metric == "jobs_created":
            date_buckets[key] = date_buckets.get(key, 0) + 1
        elif metric in ("findings_count", "findings"):
            report = await job_mgr.get_report(job.job_id)
            if report:
                date_buckets[key] = date_buckets.get(key, 0) + len(report.findings)
        elif metric == "pages_scraped":
            date_buckets[key] = date_buckets.get(key, 0) + job.pages_scraped

    return TrendResponse(
        metric=metric,
        data_points=[TrendDataPoint(date=k, value=v) for k, v in sorted(date_buckets.items())],
    )
