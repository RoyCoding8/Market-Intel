"""Engine pipeline models — internal input/output for scraping, analysis, verification."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

class PipelineState(str, Enum):
    INIT = "pending"                # matches JobStatus.PENDING
    SCRAPING = "scraping"
    ANALYZING = "analyzing"
    VERIFYING = "verifying"
    REPORTING = "generating_report"  # matches JobStatus.GENERATING_REPORT
    DONE = "completed"              # matches JobStatus.COMPLETED
    ERROR = "failed"                # matches JobStatus.FAILED

class PipelineContext(BaseModel):
    """Passed through the entire pipeline. Carries state + config."""
    job_id: str
    query: Optional[str] = None
    competitor_urls: list[str]
    focus_areas: list[str] = Field(default_factory=lambda: ["pricing", "features", "team", "news"])
    state: PipelineState = PipelineState.INIT
    max_pages_per_competitor: int = Field(default=20, ge=1, le=100)
    llm_model: str = "openai/mimo-v2.5-pro"
    verification_passes: int = Field(default=2, ge=1, le=10)

class ScrapeRequest(BaseModel):
    url: str
    focus_areas: list[str]
    max_pages: int = Field(default=20, ge=1, le=100)

class QualityVector(BaseModel):
    """Multi-dimensional page quality assessment.

    Each dimension captures a distinct signal that downstream stages
    can weight independently (e.g., pricing extractor cares about
    density + structure, news extractor cares about freshness).
    """
    density: float = Field(default=0.0, ge=0.0, le=1.0, description="Keyword relevance to page type")
    volume: float = Field(default=0.0, ge=0.0, le=1.0, description="Content length adequacy")
    structure: float = Field(default=0.0, ge=0.0, le=1.0, description="Tables, lists, headings present")
    freshness: float = Field(default=0.0, ge=0.0, le=1.0, description="Date indicators present")
    noise: float = Field(default=0.0, ge=0.0, le=1.0, description="Boilerplate ratio (lower = cleaner)")

    @property
    def composite(self) -> float:
        """Weighted composite score (backward compatible with content_quality)."""
        return max(0.0, min(1.0,
            0.3 * self.density +
            0.25 * self.volume +
            0.2 * self.structure +
            0.15 * self.freshness +
            0.1 * (1.0 - self.noise)
        ))

class ScrapedContent(BaseModel):
    url: str
    title: Optional[str] = None
    html_text: str
    page_type: str = "unknown"
    links_found: list[str] = Field(default_factory=list)
    scraped_at: datetime
    metadata: dict[str, Optional[str]] = Field(default_factory=dict)
    content_quality: float = Field(default=0.0, ge=0.0, le=1.0)
    quality_vector: Optional[QualityVector] = Field(default=None, description="Multi-dimensional quality assessment")
    content_hash: str = ""
    robots_respected: bool = True
    anti_bot_detected: Optional[str] = None

class ScrapeResult(BaseModel):
    competitor_url: str
    competitor_name: Optional[str] = None
    pages: list[ScrapedContent]
    errors: list[str] = Field(default_factory=list)
    total_pages_attempted: int = 0
    robots_respected: bool = True
    metadata: dict[str, Optional[str]] = Field(default_factory=dict)

class Claim(BaseModel):
    id: str
    text: str
    category: str
    source_url: str
    source_quote: str = Field(..., description="Exact quote from source")
    competitor_url: str
    extracted_at: datetime
    relevance: float = Field(default=0.5, ge=0.0, le=1.0, description="How relevant to the user's query (0-1)")
    reliability: float = Field(default=0.5, ge=0.0, le=1.0, description="How likely correct based on pipeline confidence (0-1)")

    @property
    def expected_value(self) -> float:
        """Decision-theoretic value: relevance × reliability."""
        return self.relevance * self.reliability

class AnalysisRequest(BaseModel):
    scrape_result: ScrapeResult
    query: Optional[str] = None
    focus_areas: list[str] = Field(default_factory=lambda: ["pricing", "features", "team", "news"])

class AnalysisResult(BaseModel):
    competitor_url: str
    competitor_name: str
    claims: list[Claim]
    pricing_data: Optional[dict] = None
    features_data: list[dict] = Field(default_factory=list)
    team_data: Optional[dict] = None
    news_data: list[dict] = Field(default_factory=list)

class VerificationRequest(BaseModel):
    claims: list[Claim]
    scrape_results: list[ScrapeResult]
    verification_passes: int = Field(default=2, ge=1, le=10)

class VerificationResult(BaseModel):
    claim_id: str
    verified: bool
    confidence: float = Field(..., ge=0.0, le=1.0)
    confidence_level: str
    reason: str
    supporting_quote: Optional[str] = None
    source_url: str
    concerns: list[str] = Field(default_factory=list)

class VerificationOutput(BaseModel):
    results: list[VerificationResult]
    total_claims: int
    verified_count: int
    flagged_count: int
    passes_completed: int

class ReportRequest(BaseModel):
    analysis_results: list[AnalysisResult]
    verification_output: VerificationOutput
    query: Optional[str] = None

class ReportOutput(BaseModel):
    executive_summary: str
    findings: list[dict] = Field(default_factory=list)
    comparison_tables: list[dict] = Field(default_factory=list)
    trend_analysis: Optional[str] = None
    recommendations: list[str] = Field(default_factory=list)
    total_sources: int = 0
    total_expected_value: float = Field(default=0.0, description="Sum of all claim expected values (relevance × reliability)")
    average_expected_value: float = Field(default=0.0, description="Average expected value across all claims")
