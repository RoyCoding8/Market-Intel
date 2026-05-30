"""SSE event schemas — emitted by Engine, consumed by Backend->Frontend."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

class EventType(str, Enum):
    JOB_STARTED = "job.started"
    JOB_COMPLETED = "job.completed"
    JOB_FAILED = "job.failed"
    JOB_CANCELLED = "job.cancelled"
    STEP_STARTED = "step.started"
    STEP_COMPLETED = "step.completed"
    STEP_FAILED = "step.failed"
    PAGE_SCRAPED = "page.scraped"
    SCRAPING_COMPLETE = "scraping.complete"
    FINDING_FOUND = "finding.found"
    COMPARISON_GENERATED = "comparison.generated"
    CLAIM_VERIFIED = "claim.verified"
    CLAIM_FLAGGED = "claim.flagged"
    VERIFICATION_COMPLETE = "verification.complete"
    REPORT_GENERATED = "report.generated"
    LOG = "log"
    PROGRESS = "progress"
    HEARTBEAT = "heartbeat"

class AgentEvent(BaseModel):
    """Base event model for all SSE events."""
    event_id: str
    event_type: EventType
    job_id: str
    agent_name: str
    timestamp: datetime
    message: str
    data: Optional[dict] = None

class ProgressData(BaseModel):
    current_step: str
    step_number: int
    total_steps: int
    progress: float = Field(..., ge=0.0, le=1.0)
    pages_scraped: int = 0
    findings_count: int = 0

class ScrapedPageEvent(BaseModel):
    url: str
    page_type: str
    title: Optional[str] = None
    content_length: int

class FindingEvent(BaseModel):
    finding_id: str
    title: str
    category: str
    confidence: str
    summary: str

class VerificationEvent(BaseModel):
    finding_id: str
    verified: bool
    confidence: str
    reason: Optional[str] = None

class ReportEvent(BaseModel):
    report_id: str
    findings_count: int
    total_citations: int
    verification_passes: int

class ErrorEvent(BaseModel):
    error_type: str
    message: str
    recoverable: bool = True
    details: Optional[str] = None
