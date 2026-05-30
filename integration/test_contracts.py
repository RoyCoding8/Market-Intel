"""Contract compliance tests for Python Pydantic models.

Verifies that all contract models can be instantiated, validate correctly,
and maintain structural consistency between api.py and engine.py.

Run with: pytest integration/test_contracts.py -v
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

# Ensure project root is importable
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from contracts.api import (
    CancelJobResponse,
    Citation,
    ComparisonRow,
    ComparisonTable,
    CompetitorData,
    CompetitorInput,
    ConfidenceLevel,
    CreateJobRequest,
    CreateJobResponse,
    DashboardStats,
    ErrorResponse,
    ExportFormat,
    ExportRequest,
    ExportResponse,
    FeatureData,
    Finding,
    HealthResponse,
    IntelligenceReport,
    JobListResponse,
    JobStatus,
    JobStatusResponse,
    NewsItem,
    PricingData,
    PricingPlan,
    ReportResponse,
    ScheduleConfig,
    ScheduleFrequency,
    ScrapedPage,
    TeamData,
    TeamMember,
    TrendDataPoint,
    TrendResponse,
    UpdateScheduleRequest,
)

from contracts.engine import (
    AnalysisRequest,
    AnalysisResult,
    Claim,
    PipelineContext,
    PipelineState,
    ReportOutput,
    ReportRequest,
    ScrapeRequest,
    ScrapeResult,
    ScrapedContent,
    VerificationOutput,
    VerificationRequest,
    VerificationResult,
)

from contracts.events import (
    AgentEvent,
    ErrorEvent,
    EventType,
    FindingEvent,
    ProgressData,
    ReportEvent,
    ScrapedPageEvent,
    VerificationEvent,
)

# ── 1. API Models — Instantiation with Valid Data ────────────────────────

class TestAPIModels:
    """Test that all API contract models can be instantiated with valid data."""

    def test_competitor_input_basic(self):
        c = CompetitorInput(url="https://example.com")
        assert c.url == "https://example.com"
        assert c.focus_areas == ["pricing", "features", "team", "news"]

    def test_competitor_input_full(self):
        c = CompetitorInput(
            url="https://example.com",
            name="Example Inc",
            focus_areas=["pricing", "features"],
        )
        assert c.name == "Example Inc"
        assert c.focus_areas == ["pricing", "features"]

    def test_competitor_input_url_auto_prepends_https(self):
        c = CompetitorInput(url="example.com")
        assert c.url.startswith("https://")

    def test_scraped_page(self):
        page = ScrapedPage(
            url="https://example.com/pricing",
            page_type="pricing",
            title="Pricing",
            content_hash="abc123",
            scraped_at=datetime.now(timezone.utc),
            raw_text="Some content",
        )
        assert page.page_type == "pricing"

    def test_pricing_plan(self):
        plan = PricingPlan(
            name="Pro",
            price="$99/mo",
            billing_period="monthly",
            features=["Feature A", "Feature B"],
            highlighted=True,
        )
        assert plan.highlighted is True

    def test_pricing_data(self):
        data = PricingData(
            plans=[PricingPlan(name="Free", features=[])],
            source_url="https://example.com/pricing",
            scraped_at=datetime.now(timezone.utc),
        )
        assert data.currency == "USD"
        assert data.has_free_tier is False

    def test_feature_data(self):
        f = FeatureData(
            name="API Access",
            description="REST API",
            category="Developer",
            source_url="https://example.com",
        )
        assert f.name == "API Access"

    def test_team_member(self):
        m = TeamMember(name="Jane Doe", role="CEO")
        assert m.name == "Jane Doe"

    def test_team_data(self):
        td = TeamData(
            team_size="11-50",
            key_members=[TeamMember(name="Jane", role="CEO")],
            recent_hires=[],
            source_url="https://example.com/about",
        )
        assert td.team_size == "11-50"

    def test_news_item(self):
        n = NewsItem(
            title="New Feature Launch",
            url="https://example.com/blog/1",
            date=datetime.now(timezone.utc),
            summary="We launched a new feature.",
            source="company_blog",
        )
        assert n.source == "company_blog"

    def test_competitor_data(self):
        cd = CompetitorData(
            id="comp-1",
            name="Acme",
            url="https://acme.com",
            scraped_pages=[],
            features=[],
            recent_news=[],
            last_updated=datetime.now(timezone.utc),
        )
        assert cd.id == "comp-1"

    def test_citation(self):
        c = Citation(
            url="https://example.com",
            title="Example",
            quote="Exact quote from source",
            accessed_at=datetime.now(timezone.utc),
            confidence=ConfidenceLevel.HIGH,
        )
        assert c.confidence == ConfidenceLevel.HIGH

    def test_finding(self):
        f = Finding(
            id="f-1",
            title="Test Finding",
            summary="Summary text",
            category="pricing",
            confidence=ConfidenceLevel.HIGH,
            confidence_score=0.95,
            citations=[],
            competitor_ids=["comp-1"],
            impact="High impact",
            recommendation="Do something",
        )
        assert f.confidence_score == 0.95

    def test_comparison_row(self):
        row = ComparisonRow(
            dimension="Free tier",
            values={"comp-1": "Yes", "comp-2": "No"},
            winner="comp-1",
        )
        assert row.dimension == "Free tier"

    def test_comparison_table(self):
        table = ComparisonTable(
            title="Pricing",
            dimensions=["Free tier"],
            rows=[
                ComparisonRow(
                    dimension="Free tier",
                    values={"comp-1": "Yes", "comp-2": "No"},
                )
            ],
            competitor_ids=["comp-1", "comp-2"],
        )
        assert len(table.rows) == 1

    def test_intelligence_report(self):
        report = IntelligenceReport(
            id="r-1",
            title="Report",
            created_at=datetime.now(timezone.utc),
            competitors=[],
            findings=[],
            executive_summary="Summary",
            recommendations=["Do this"],
            total_sources=10,
            verification_passes=2,
        )
        assert report.total_sources == 10

    def test_create_job_request(self):
        req = CreateJobRequest(
            competitors=[CompetitorInput(url="https://example.com")],
            query="pricing analysis",
        )
        assert len(req.competitors) == 1
        assert req.query == "pricing analysis"

    def test_create_job_response(self):
        resp = CreateJobResponse(
            job_id="abc123",
            status=JobStatus.PENDING,
            message="Job created",
        )
        assert resp.status == JobStatus.PENDING

    def test_job_status_response(self):
        resp = JobStatusResponse(
            job_id="abc",
            status=JobStatus.SCRAPING,
            progress=0.5,
            competitors_found=2,
            pages_scraped=4,
            findings_count=0,
        )
        assert resp.progress == 0.5

    def test_health_response(self):
        resp = HealthResponse()
        assert resp.status == "ok"
        assert resp.version == "0.3.0"

    def test_cancel_job_response(self):
        resp = CancelJobResponse(
            job_id="abc",
            status=JobStatus.CANCELLED,
            message="Cancelled",
        )
        assert resp.status == JobStatus.CANCELLED

    def test_export_request(self):
        req = ExportRequest(
            format=ExportFormat.JSON,
            include_citations=True,
            include_raw_data=False,
        )
        assert req.format == ExportFormat.JSON

    def test_export_response(self):
        resp = ExportResponse(
            job_id="abc",
            format=ExportFormat.CSV,
            content="col1,col2\n1,2",
        )
        assert resp.content is not None

    def test_schedule_config(self):
        config = ScheduleConfig(
            frequency=ScheduleFrequency.DAILY,
            next_run=datetime.now(timezone.utc),
        )
        assert config.frequency == ScheduleFrequency.DAILY

    def test_dashboard_stats(self):
        stats = DashboardStats(
            total_jobs=10,
            completed_jobs=8,
            failed_jobs=2,
            total_findings=47,
            high_confidence_findings=31,
            total_competitors_tracked=8,
            total_pages_scraped=156,
            total_verifications=12,
            average_confidence_score=0.84,
            jobs_last_7_days=5,
        )
        assert stats.total_jobs == 10

    def test_trend_data_point(self):
        dp = TrendDataPoint(date="2025-06-15", value=5.0, label="5 findings")
        assert dp.value == 5.0

    def test_trend_response(self):
        resp = TrendResponse(
            metric="findings",
            data_points=[TrendDataPoint(date="2025-06-15", value=5.0)],
        )
        assert resp.metric == "findings"

    def test_error_response(self):
        resp = ErrorResponse(error="Not found", status_code=404)
        assert resp.status_code == 404

    def test_job_list_response(self):
        resp = JobListResponse(jobs=[], total=0)
        assert resp.total == 0

    def test_report_response(self):
        report = IntelligenceReport(
            id="r-1",
            title="Report",
            created_at=datetime.now(timezone.utc),
            competitors=[],
            findings=[],
            executive_summary="Summary",
        )
        resp = ReportResponse(report=report)
        assert resp.report.id == "r-1"

    def test_update_schedule_request(self):
        req = UpdateScheduleRequest(enabled=False)
        assert req.enabled is False

    def test_update_schedule_request_partial(self):
        req = UpdateScheduleRequest(frequency=ScheduleFrequency.WEEKLY)
        assert req.frequency == ScheduleFrequency.WEEKLY
        assert req.enabled is None

# ── 2. Required Field Validation ─────────────────────────────────────────

class TestRequiredFields:
    """Test that missing required fields raise validation errors."""

    def test_competitor_input_requires_url(self):
        with pytest.raises(Exception):
            CompetitorInput()  # type: ignore

    def test_citation_requires_quote(self):
        with pytest.raises(Exception):
            Citation(
                url="https://example.com",
                accessed_at=datetime.now(timezone.utc),
                confidence=ConfidenceLevel.HIGH,
            )  # type: ignore

    def test_finding_requires_title(self):
        with pytest.raises(Exception):
            Finding(
                id="f-1",
                summary="Summary",
                category="pricing",
                confidence=ConfidenceLevel.HIGH,
                confidence_score=0.5,
            )  # type: ignore

    def test_create_job_request_requires_competitors(self):
        with pytest.raises(Exception):
            CreateJobRequest()  # type: ignore

    def test_finding_requires_confidence_score(self):
        with pytest.raises(Exception):
            Finding(
                id="f-1",
                title="Title",
                summary="Summary",
                category="pricing",
                confidence=ConfidenceLevel.HIGH,
            )  # type: ignore

    def test_intelligence_report_requires_title(self):
        with pytest.raises(Exception):
            IntelligenceReport(
                id="r-1",
                created_at=datetime.now(timezone.utc),
                competitors=[],
                findings=[],
                executive_summary="Summary",
            )  # type: ignore

    def test_agent_event_requires_event_type(self):
        with pytest.raises(Exception):
            AgentEvent(
                event_id="e-1",
                job_id="j-1",
                agent_name="backend",
                timestamp=datetime.now(timezone.utc),
                message="test",
            )  # type: ignore

    def test_scraped_content_requires_url(self):
        with pytest.raises(Exception):
            ScrapedContent(
                html_text="content",
                scraped_at=datetime.now(timezone.utc),
            )  # type: ignore

# ── 3. Enum Value Consistency ────────────────────────────────────────────

class TestEnumConsistency:
    """Verify enum values match between Python and TypeScript definitions."""

    def test_job_status_values(self):
        expected = {
            "pending", "scraping", "analyzing", "verifying",
            "generating_report", "completed", "failed", "cancelled",
        }
        actual = {s.value for s in JobStatus}
        assert actual == expected

    def test_confidence_level_values(self):
        expected = {"high", "medium", "low", "very_low"}
        actual = {c.value for c in ConfidenceLevel}
        assert actual == expected

    def test_schedule_frequency_values(self):
        expected = {"once", "hourly", "daily", "weekly", "custom"}
        actual = {f.value for f in ScheduleFrequency}
        assert actual == expected

    def test_export_format_values(self):
        expected = {"json", "csv", "markdown", "pdf"}
        actual = {f.value for f in ExportFormat}
        assert actual == expected

    def test_event_type_values_match_typescript(self):
        """Verify EventType enum matches the TypeScript EventType union."""
        expected = {
            "job.started", "job.completed", "job.failed", "job.cancelled",
            "step.started", "step.completed", "step.failed",
            "page.scraped", "scraping.complete",
            "finding.found", "comparison.generated",
            "claim.verified", "claim.flagged", "verification.complete",
            "report.generated", "log", "progress", "heartbeat",
        }
        actual = {e.value for e in EventType}
        assert actual == expected

    def test_pipeline_state_values(self):
        expected = {
            "pending", "scraping", "analyzing", "verifying",
            "generating_report", "completed", "failed",
        }
        actual = {s.value for s in PipelineState}
        assert actual == expected

# ── 4. Forward Reference Resolution ──────────────────────────────────────

class TestForwardReferences:
    """Test that forward references resolve correctly."""

    def test_competitor_data_uses_scraped_page(self):
        """ScrapedPage is referenced in CompetitorData.scraped_pages."""
        page = ScrapedPage(
            url="https://example.com",
            page_type="pricing",
            content_hash="hash",
            scraped_at=datetime.now(timezone.utc),
            raw_text="content",
        )
        cd = CompetitorData(
            id="c1",
            name="Test",
            url="https://example.com",
            scraped_pages=[page],
            features=[],
            recent_news=[],
            last_updated=datetime.now(timezone.utc),
        )
        assert len(cd.scraped_pages) == 1

    def test_competitor_data_uses_pricing_data(self):
        """PricingData is referenced in CompetitorData.pricing."""
        pd = PricingData(
            plans=[PricingPlan(name="Free", features=[])],
            source_url="https://example.com",
            scraped_at=datetime.now(timezone.utc),
        )
        cd = CompetitorData(
            id="c1",
            name="Test",
            url="https://example.com",
            scraped_pages=[],
            pricing=pd,
            features=[],
            recent_news=[],
            last_updated=datetime.now(timezone.utc),
        )
        assert cd.pricing is not None

    def test_intelligence_report_uses_finding(self):
        """Finding is referenced in IntelligenceReport.findings."""
        f = Finding(
            id="f-1",
            title="Title",
            summary="Summary",
            category="pricing",
            confidence=ConfidenceLevel.HIGH,
            confidence_score=0.9,
            citations=[],
            competitor_ids=[],
        )
        report = IntelligenceReport(
            id="r-1",
            title="Report",
            created_at=datetime.now(timezone.utc),
            competitors=[],
            findings=[f],
            executive_summary="Summary",
        )
        assert len(report.findings) == 1

    def test_intelligence_report_uses_competitor_data(self):
        """CompetitorData is referenced in IntelligenceReport.competitors."""
        cd = CompetitorData(
            id="c1",
            name="Test",
            url="https://example.com",
            scraped_pages=[],
            features=[],
            recent_news=[],
            last_updated=datetime.now(timezone.utc),
        )
        report = IntelligenceReport(
            id="r-1",
            title="Report",
            created_at=datetime.now(timezone.utc),
            competitors=[cd],
            findings=[],
            executive_summary="Summary",
        )
        assert len(report.competitors) == 1

    def test_engine_forward_refs(self):
        """Engine models that reference other engine models work."""
        sc = ScrapedContent(
            url="https://example.com",
            html_text="content",
            scraped_at=datetime.now(timezone.utc),
        )
        sr = ScrapeResult(
            competitor_url="https://example.com",
            pages=[sc],
        )
        claim = Claim(
            id="c-1",
            text="A claim",
            category="pricing",
            source_url="https://example.com",
            source_quote="Exact quote",
            competitor_url="https://example.com",
            extracted_at=datetime.now(timezone.utc),
        )
        vr = VerificationResult(
            claim_id="c-1",
            verified=True,
            confidence=0.9,
            confidence_level="high",
            reason="Verified against source",
            source_url="https://example.com",
        )
        vo = VerificationOutput(
            results=[vr],
            total_claims=1,
            verified_count=1,
            flagged_count=0,
            passes_completed=2,
        )
        assert vo.total_claims == 1

# ── 5. Field Type Consistency ────────────────────────────────────────────

class TestFieldTypes:
    """Verify field types are consistent between api.py and engine.py."""

    def test_finding_confidence_is_enum(self):
        f = Finding(
            id="f-1",
            title="T",
            summary="S",
            category="pricing",
            confidence=ConfidenceLevel.HIGH,
            confidence_score=0.9,
        )
        assert isinstance(f.confidence, ConfidenceLevel)

    def test_citation_confidence_is_enum(self):
        c = Citation(
            url="https://example.com",
            quote="quote",
            accessed_at=datetime.now(timezone.utc),
            confidence=ConfidenceLevel.MEDIUM,
        )
        assert isinstance(c.confidence, ConfidenceLevel)

    def test_job_status_is_enum(self):
        resp = JobStatusResponse(
            job_id="j",
            status=JobStatus.SCRAPING,
            progress=0.0,
            competitors_found=0,
            pages_scraped=0,
            findings_count=0,
        )
        assert isinstance(resp.status, JobStatus)

    def test_pipeline_state_is_enum(self):
        ctx = PipelineContext(
            job_id="j",
            competitor_urls=["https://example.com"],
        )
        assert isinstance(ctx.state, PipelineState)

    def test_agent_event_type_is_enum(self):
        event = AgentEvent(
            event_id="e-1",
            event_type=EventType.JOB_STARTED,
            job_id="j-1",
            agent_name="backend",
            timestamp=datetime.now(timezone.utc),
            message="Started",
        )
        assert isinstance(event.event_type, EventType)

    def test_finding_confidence_score_is_float(self):
        f = Finding(
            id="f-1",
            title="T",
            summary="S",
            category="pricing",
            confidence=ConfidenceLevel.HIGH,
            confidence_score=0.95,
        )
        assert isinstance(f.confidence_score, float)

    def test_job_status_progress_is_float(self):
        resp = JobStatusResponse(
            job_id="j",
            status=JobStatus.PENDING,
            progress=0.0,
            competitors_found=0,
            pages_scraped=0,
            findings_count=0,
        )
        assert isinstance(resp.progress, float)

# ── 6. Validation Constraints ────────────────────────────────────────────

class TestValidationConstraints:
    """Test field constraints (ge, le, max_length, etc.)."""

    def test_finding_confidence_score_ge_0(self):
        with pytest.raises(Exception):
            Finding(
                id="f-1",
                title="T",
                summary="S",
                category="pricing",
                confidence=ConfidenceLevel.HIGH,
                confidence_score=-0.1,
            )

    def test_finding_confidence_score_le_1(self):
        with pytest.raises(Exception):
            Finding(
                id="f-1",
                title="T",
                summary="S",
                category="pricing",
                confidence=ConfidenceLevel.HIGH,
                confidence_score=1.1,
            )

    def test_job_status_progress_ge_0(self):
        with pytest.raises(Exception):
            JobStatusResponse(
                job_id="j",
                status=JobStatus.PENDING,
                progress=-0.1,
                competitors_found=0,
                pages_scraped=0,
                findings_count=0,
            )

    def test_job_status_progress_le_1(self):
        with pytest.raises(Exception):
            JobStatusResponse(
                job_id="j",
                status=JobStatus.PENDING,
                progress=1.1,
                competitors_found=0,
                pages_scraped=0,
                findings_count=0,
            )

    def test_create_job_request_min_competitors(self):
        with pytest.raises(Exception):
            CreateJobRequest(competitors=[])

    def test_competitor_input_url_max_length(self):
        long_url = "https://example.com/" + "a" * 3000
        with pytest.raises(Exception):
            CompetitorInput(url=long_url)

    def test_competitor_input_name_max_length(self):
        long_name = "A" * 201
        with pytest.raises(Exception):
            CompetitorInput(url="https://example.com", name=long_name)

    def test_scraped_content_content_quality_range(self):
        with pytest.raises(Exception):
            ScrapedContent(
                url="https://example.com",
                html_text="content",
                scraped_at=datetime.now(timezone.utc),
                content_quality=1.5,
            )

    def test_verification_result_confidence_range(self):
        with pytest.raises(Exception):
            VerificationResult(
                claim_id="c-1",
                verified=True,
                confidence=1.5,
                confidence_level="high",
                reason="Verified",
                source_url="https://example.com",
            )

# ── 7. Enum Str Compatibility ────────────────────────────────────────────

class TestEnumStrCompatibility:
    """Test that enums work as strings (str, Enum mixin)."""

    def test_job_status_as_string(self):
        assert JobStatus.PENDING == "pending"
        assert JobStatus.SCRAPING == "scraping"
        assert JobStatus.COMPLETED == "completed"

    def test_confidence_level_as_string(self):
        assert ConfidenceLevel.HIGH == "high"
        assert ConfidenceLevel.MEDIUM == "medium"
        assert ConfidenceLevel.LOW == "low"

    def test_export_format_as_string(self):
        assert ExportFormat.JSON == "json"
        assert ExportFormat.CSV == "csv"
        assert ExportFormat.MARKDOWN == "markdown"
        assert ExportFormat.PDF == "pdf"

    def test_schedule_frequency_as_string(self):
        assert ScheduleFrequency.ONCE == "once"
        assert ScheduleFrequency.DAILY == "daily"
        assert ScheduleFrequency.WEEKLY == "weekly"

    def test_event_type_as_string(self):
        assert EventType.JOB_STARTED == "job.started"
        assert EventType.JOB_COMPLETED == "job.completed"
        assert EventType.PROGRESS == "progress"

    def test_pipeline_state_as_string(self):
        assert PipelineState.INIT == "pending"
        assert PipelineState.SCRAPING == "scraping"
        assert PipelineState.DONE == "completed"
        assert PipelineState.REPORTING == "generating_report"
        assert PipelineState.ERROR == "failed"
