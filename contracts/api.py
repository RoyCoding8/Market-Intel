"""API request/response models — used by Backend and Frontend."""

from __future__ import annotations

import ipaddress
import re
import socket
from datetime import datetime
from enum import Enum
from typing import Optional
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator, model_validator



class JobStatus(str, Enum):
    PENDING = "pending"
    SCRAPING = "scraping"
    ANALYZING = "analyzing"
    VERIFYING = "verifying"
    GENERATING_REPORT = "generating_report"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    VERY_LOW = "very_low"

class ScheduleFrequency(str, Enum):
    ONCE = "once"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    CUSTOM = "custom"

class ExportFormat(str, Enum):
    JSON = "json"
    CSV = "csv"
    MARKDOWN = "markdown"
    PDF = "pdf"



class CompetitorInput(BaseModel):
    url: str = Field(..., description="Competitor website URL", max_length=2048)
    name: Optional[str] = Field(None, description="Friendly name (auto-detected if omitted)", max_length=200)
    focus_areas: list[str] = Field(
        default_factory=lambda: ["pricing", "features", "team", "news"],
        description="Areas to focus scraping on",
    )

    @staticmethod
    def _is_blocked_ip(ip_str: str) -> str | None:
        """Check if an IP address string is in a blocked range. Returns reason or None."""
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            return None
        if ip.is_loopback:
            return f"Requests to loopback addresses are not allowed ({ip_str})"
        if ip.is_private:
            return f"Requests to private IP addresses are not allowed ({ip_str})"
        if ip.is_link_local:
            return f"Requests to link-local addresses are not allowed ({ip_str})"
        if ip.is_reserved:
            return f"Requests to reserved IP addresses are not allowed ({ip_str})"
        if str(ip) == "169.254.169.254":
            return "Requests to cloud metadata endpoints are not allowed"
        return None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("URL cannot be empty")
        if "://" in v:
            scheme = v.split("://")[0].lower()
            if scheme not in ("http", "https"):
                raise ValueError(f"URL scheme must be http or https, got: {scheme}")
        else:
            v = f"https://{v}"

        parsed = urlparse(v)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"URL scheme must be http or https, got: {parsed.scheme}")
        if not parsed.netloc:
            raise ValueError("URL must have a valid hostname")

        hostname = (parsed.hostname or "").lower().rstrip(".")
        if not hostname:
            raise ValueError("URL must have a valid hostname")

        # Block known metadata hostnames
        if hostname in {"metadata.google.internal", "instance-data"}:
            raise ValueError("Requests to cloud metadata endpoints are not allowed")

        if hostname == "localhost":
            raise ValueError("Requests to localhost are not allowed")

        # Block octal/hex IP bypasses (e.g. 0177.0.0.1, 0x7f.0x00.0x00.0x01)
        if re.match(r"^(0\d+\.|0x[0-9a-f]+\.)(\d+\.){2}\d+$", hostname, re.IGNORECASE):
            raise ValueError(f"Requests to non-canonical IP addresses are not allowed ({hostname})")
        if re.match(r"^0x[0-9a-f]+(\.0x[0-9a-f]+){3}$", hostname, re.IGNORECASE):
            raise ValueError(f"Requests to non-canonical IP addresses are not allowed ({hostname})")

        # If hostname is a literal IP, check against blocked ranges
        try:
            ip = ipaddress.ip_address(hostname)
            reason = cls._is_blocked_ip(str(ip))
            if reason:
                raise ValueError(reason)
        except ValueError as e:
            if "not allowed" in str(e) or "non-canonical" in str(e):
                raise
            if "." not in hostname and ":" not in hostname:
                raise ValueError(f"Invalid hostname: {hostname!r} (must be a valid domain or IP)")

        # DNS resolution — blocks wildcard DNS (nip.io, sslip.io, etc.)
        try:
            addrinfos = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
            for family, _, _, _, sockaddr in addrinfos:
                resolved_ip = sockaddr[0]
                reason = cls._is_blocked_ip(resolved_ip)
                if reason:
                    raise ValueError(reason)
        except socket.gaierror:
            pass

        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = re.sub(r"<[^>]+>", "", v.strip())
        v = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", v)
        return v or None


class ScrapedPage(BaseModel):
    url: str
    page_type: str
    title: Optional[str] = None
    content_hash: str
    scraped_at: datetime
    raw_text: str

class PricingPlan(BaseModel):
    name: str
    price: Optional[str] = None
    billing_period: Optional[str] = None
    features: list[str] = Field(default_factory=list)
    highlighted: bool = False

class PricingData(BaseModel):
    plans: list[PricingPlan]
    currency: str = "USD"
    has_free_tier: bool = False
    enterprise_tier: bool = False
    source_url: str
    scraped_at: datetime

class FeatureData(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    competitor_advantage: Optional[str] = None
    source_url: str

class TeamMember(BaseModel):
    name: str
    role: Optional[str] = None
    linkedin_url: Optional[str] = None

class TeamData(BaseModel):
    team_size: Optional[str] = None
    key_members: list[TeamMember] = Field(default_factory=list)
    recent_hires: list[TeamMember] = Field(default_factory=list)
    source_url: str

class NewsItem(BaseModel):
    title: str
    url: str
    date: Optional[datetime] = None
    summary: Optional[str] = None
    source: str

class CompetitorData(BaseModel):
    id: str
    name: str
    url: str
    logo_url: Optional[str] = None
    scraped_pages: list[ScrapedPage] = Field(default_factory=list)
    pricing: Optional[PricingData] = None
    features: list[FeatureData] = Field(default_factory=list)
    team_info: Optional[TeamData] = None
    recent_news: list[NewsItem] = Field(default_factory=list)
    last_updated: datetime



class Citation(BaseModel):
    url: str
    title: Optional[str] = None
    quote: str = Field(..., description="Exact quote from source supporting this claim")
    accessed_at: datetime
    confidence: ConfidenceLevel



class Finding(BaseModel):
    id: str
    title: str
    summary: str
    category: str
    confidence: ConfidenceLevel
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    citations: list[Citation] = Field(default_factory=list)
    competitor_ids: list[str] = Field(default_factory=list)
    impact: Optional[str] = None
    recommendation: Optional[str] = None

class ComparisonRow(BaseModel):
    dimension: str
    values: dict[str, str]
    winner: Optional[str] = None

class ComparisonTable(BaseModel):
    title: str
    dimensions: list[str]
    rows: list[ComparisonRow]
    competitor_ids: list[str]



class IntelligenceReport(BaseModel):
    id: str
    title: str
    created_at: datetime
    competitors: list[CompetitorData]
    findings: list[Finding]
    comparison_tables: list[ComparisonTable] = Field(default_factory=list)
    executive_summary: str
    trend_analysis: Optional[str] = None
    recommendations: list[str] = Field(default_factory=list)
    total_sources: int = 0
    verification_passes: int = 0



class ScheduleConfig(BaseModel):
    frequency: ScheduleFrequency
    cron_expression: Optional[str] = None
    next_run: Optional[datetime] = None

    @model_validator(mode="after")
    def validate_custom_cron(self) -> "ScheduleConfig":
        if self.frequency == ScheduleFrequency.CUSTOM and not (self.cron_expression or "").strip():
            raise ValueError("custom schedules require cron_expression")
        return self

class CreateJobRequest(BaseModel):
    competitors: list[CompetitorInput] = Field(..., min_length=1, max_length=10)
    query: Optional[str] = Field(None, max_length=10000, description="Optional focus query e.g. 'pricing changes'")
    schedule: Optional[ScheduleConfig] = None

class CreateJobResponse(BaseModel):
    job_id: str
    status: JobStatus
    message: str

class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: float = Field(..., ge=0.0, le=1.0, description="0.0 to 1.0")
    current_step: Optional[str] = None
    competitors_found: int = 0
    pages_scraped: int = 0
    findings_count: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

class ReportResponse(BaseModel):
    report: IntelligenceReport

class JobListResponse(BaseModel):
    jobs: list[JobStatusResponse]
    total: int



class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.3.0"
    llm_configured: bool = False
    bright_data_configured: bool = False
    scheduler_running: bool = False
    active_jobs: int = 0
    total_jobs_completed: int = 0

class CancelJobResponse(BaseModel):
    job_id: str
    status: JobStatus
    message: str



class ExportRequest(BaseModel):
    format: ExportFormat
    include_citations: bool = True
    include_raw_data: bool = False

class ExportResponse(BaseModel):
    job_id: str
    format: ExportFormat
    content: Optional[str] = None
    download_url: Optional[str] = None



class ScheduledJobResponse(BaseModel):
    schedule_id: str
    job_config: CreateJobRequest
    frequency: ScheduleFrequency
    cron_expression: Optional[str] = None
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    last_job_id: Optional[str] = None
    enabled: bool = True
    created_at: datetime

class ScheduledJobListResponse(BaseModel):
    schedules: list[ScheduledJobResponse]
    total: int

class UpdateScheduleRequest(BaseModel):
    enabled: Optional[bool] = None
    frequency: Optional[ScheduleFrequency] = None
    cron_expression: Optional[str] = None



class DashboardStats(BaseModel):
    total_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    total_findings: int = 0
    high_confidence_findings: int = 0
    total_competitors_tracked: int = 0
    total_pages_scraped: int = 0
    total_verifications: int = 0
    average_confidence_score: float = 0.0
    jobs_last_7_days: int = 0
    findings_by_category: dict[str, int] = Field(default_factory=dict)
    top_competitors: list[dict] = Field(default_factory=list)

class TrendDataPoint(BaseModel):
    date: str
    value: float
    label: Optional[str] = None

class TrendResponse(BaseModel):
    metric: str
    data_points: list[TrendDataPoint]



class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    status_code: int
