"""Tests for the pipeline orchestrator."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from contracts.engine import (
    AnalysisResult,
    Claim,
    PipelineContext,
    PipelineState,
    ReportOutput,
    ScrapeResult,
    ScrapedContent,
    VerificationOutput,
    VerificationResult,
)
from contracts.events import AgentEvent, EventType
from engine.emitter import EventEmitter
from engine.pipeline import run_pipeline


class InMemoryEmitter(EventEmitter):
    """Test emitter that collects all events in memory."""

    def __init__(self):
        self.events: list[AgentEvent] = []

    async def emit(self, event: AgentEvent) -> None:
        self.events.append(event)


def _make_ctx(**overrides) -> PipelineContext:
    defaults = {
        "job_id": "test-job-001",
        "query": "Compare pricing",
        "competitor_urls": ["https://acme.com"],
        "focus_areas": ["pricing", "features"],
        "max_pages_per_competitor": 5,
        "llm_model": "test-model",
        "verification_passes": 2,
    }
    defaults.update(overrides)
    return PipelineContext(**defaults)


def _mock_scrape_result(url: str = "https://acme.com", name: str = "Acme") -> ScrapeResult:
    return ScrapeResult(
        competitor_url=url,
        competitor_name=name,
        pages=[
            ScrapedContent(
                url=url,
                title=f"{name} Home",
                html_text=f"Welcome to {name}. Pricing: $9/mo.",
                page_type="homepage",
                scraped_at=datetime.now(timezone.utc),
            ),
        ],
        errors=[],
        total_pages_attempted=1,
    )


def _mock_analysis_result(url: str = "https://acme.com", name: str = "Acme") -> AnalysisResult:
    return AnalysisResult(
        competitor_url=url,
        competitor_name=name,
        claims=[
            Claim(
                id="claim-1",
                text=f"{name} offers a $9/mo plan",
                category="pricing",
                source_url=url,
                source_quote="Pricing: $9/mo.",
                competitor_url=url,
                extracted_at=datetime.now(timezone.utc),
            ),
        ],
        pricing_data={"plans": [{"name": "Starter", "price": "$9/mo"}]},
    )


def _mock_verification_output() -> VerificationOutput:
    return VerificationOutput(
        results=[
            VerificationResult(
                claim_id="claim-1",
                verified=True,
                confidence=0.9,
                confidence_level="high",
                reason="Supported by source.",
                supporting_quote="Pricing: $9/mo.",
                source_url="https://acme.com",
            ),
        ],
        total_claims=1,
        verified_count=1,
        flagged_count=0,
        passes_completed=2,
    )


def _mock_report_output() -> ReportOutput:
    return ReportOutput(
        executive_summary="Acme offers competitive pricing.",
        findings=[{
            "title": "Low Pricing",
            "summary": "Acme starts at $9/mo",
            "category": "pricing",
            "confidence": "high",
            "confidence_score": 0.9,
            "citations": [{"url": "https://acme.com", "quote": "$9/mo", "page_type": "homepage"}],
        }],
        comparison_tables=[],
        recommendations=["Match Acme's pricing"],
        total_sources=1,
    )


@pytest.mark.asyncio
async def test_pipeline_full_run():
    """Full pipeline should produce a report and emit events."""
    ctx = _make_ctx()
    emitter = InMemoryEmitter()

    with (
        patch("engine.pipeline.scrape_competitor", new_callable=AsyncMock) as mock_scrape,
        patch("engine.pipeline.analyze_competitor", new_callable=AsyncMock) as mock_analyze,
        patch("engine.pipeline.verify_claims", new_callable=AsyncMock) as mock_verify,
        patch("engine.pipeline.generate_report", new_callable=AsyncMock) as mock_report,
    ):
        mock_scrape.return_value = _mock_scrape_result()
        mock_analyze.return_value = _mock_analysis_result()
        mock_verify.return_value = _mock_verification_output()
        mock_report.return_value = _mock_report_output()

        result = await run_pipeline(ctx, emitter)

    assert result.executive_summary == "Acme offers competitive pricing."
    assert len(result.findings) == 1
    assert ctx.state == PipelineState.DONE

    # Verify event sequence
    event_types = [e.event_type for e in emitter.events]
    assert EventType.JOB_STARTED in event_types
    assert EventType.STEP_STARTED in event_types
    assert EventType.PAGE_SCRAPED in event_types
    assert EventType.FINDING_FOUND in event_types
    assert EventType.CLAIM_VERIFIED in event_types
    assert EventType.REPORT_GENERATED in event_types
    assert EventType.JOB_COMPLETED in event_types


@pytest.mark.asyncio
async def test_pipeline_emits_page_scraped_events():
    """Each scraped page should emit a page.scraped event."""
    ctx = _make_ctx()
    emitter = InMemoryEmitter()

    with (
        patch("engine.pipeline.scrape_competitor", new_callable=AsyncMock) as mock_scrape,
        patch("engine.pipeline.analyze_competitor", new_callable=AsyncMock) as mock_analyze,
        patch("engine.pipeline.verify_claims", new_callable=AsyncMock) as mock_verify,
        patch("engine.pipeline.generate_report", new_callable=AsyncMock) as mock_report,
    ):
        mock_scrape.return_value = _mock_scrape_result()
        mock_analyze.return_value = _mock_analysis_result()
        mock_verify.return_value = _mock_verification_output()
        mock_report.return_value = _mock_report_output()

        await run_pipeline(ctx, emitter)

    page_events = [e for e in emitter.events if e.event_type == EventType.PAGE_SCRAPED]
    assert len(page_events) >= 1
    assert page_events[0].data is not None
    assert "url" in page_events[0].data


@pytest.mark.asyncio
async def test_pipeline_handles_scrape_failure():
    """Pipeline should fail gracefully when scraping produces no results."""
    ctx = _make_ctx()
    emitter = InMemoryEmitter()

    with patch("engine.pipeline.scrape_competitor", new_callable=AsyncMock) as mock_scrape:
        # Return empty result (no pages)
        mock_scrape.return_value = ScrapeResult(
            competitor_url="https://acme.com",
            pages=[],
            errors=["Connection refused"],
        )

        result = await run_pipeline(ctx, emitter)

    assert ctx.state == PipelineState.ERROR
    assert "failed" in result.executive_summary.lower()
    assert EventType.JOB_FAILED in [e.event_type for e in emitter.events]


@pytest.mark.asyncio
async def test_pipeline_handles_analysis_failure():
    """Pipeline should fail when analysis produces no results."""
    ctx = _make_ctx()
    emitter = InMemoryEmitter()

    with (
        patch("engine.pipeline.scrape_competitor", new_callable=AsyncMock) as mock_scrape,
        patch("engine.pipeline.analyze_competitor", new_callable=AsyncMock) as mock_analyze,
    ):
        mock_scrape.return_value = _mock_scrape_result()
        mock_analyze.side_effect = Exception("Analysis error")

        await run_pipeline(ctx, emitter)

    assert ctx.state == PipelineState.ERROR


@pytest.mark.asyncio
async def test_pipeline_handles_verification_failure():
    """Pipeline should continue with empty verification on verification failure."""
    ctx = _make_ctx()
    emitter = InMemoryEmitter()

    with (
        patch("engine.pipeline.scrape_competitor", new_callable=AsyncMock) as mock_scrape,
        patch("engine.pipeline.analyze_competitor", new_callable=AsyncMock) as mock_analyze,
        patch("engine.pipeline.verify_claims", new_callable=AsyncMock) as mock_verify,
        patch("engine.pipeline.generate_report", new_callable=AsyncMock) as mock_report,
    ):
        mock_scrape.return_value = _mock_scrape_result()
        mock_analyze.return_value = _mock_analysis_result()
        mock_verify.side_effect = Exception("Verification error")
        mock_report.return_value = _mock_report_output()

        result = await run_pipeline(ctx, emitter)

    # Pipeline should still complete (verification failure is non-fatal)
    assert result.executive_summary == "Acme offers competitive pricing."


@pytest.mark.asyncio
async def test_pipeline_handles_report_failure():
    """Pipeline should return a minimal report on report generation failure."""
    ctx = _make_ctx()
    emitter = InMemoryEmitter()

    with (
        patch("engine.pipeline.scrape_competitor", new_callable=AsyncMock) as mock_scrape,
        patch("engine.pipeline.analyze_competitor", new_callable=AsyncMock) as mock_analyze,
        patch("engine.pipeline.verify_claims", new_callable=AsyncMock) as mock_verify,
        patch("engine.pipeline.generate_report", new_callable=AsyncMock) as mock_report,
    ):
        mock_scrape.return_value = _mock_scrape_result()
        mock_analyze.return_value = _mock_analysis_result()
        mock_verify.return_value = _mock_verification_output()
        mock_report.side_effect = Exception("Report error")

        result = await run_pipeline(ctx, emitter)

    assert "failed" in result.executive_summary.lower()
    assert ctx.state == PipelineState.ERROR  # Report failure is an error state


@pytest.mark.asyncio
async def test_pipeline_multiple_competitors():
    """Pipeline should process multiple competitor URLs."""
    ctx = _make_ctx(competitor_urls=["https://acme.com", "https://widget.co"])
    emitter = InMemoryEmitter()

    with (
        patch("engine.pipeline.scrape_competitor", new_callable=AsyncMock) as mock_scrape,
        patch("engine.pipeline.analyze_competitor", new_callable=AsyncMock) as mock_analyze,
        patch("engine.pipeline.verify_claims", new_callable=AsyncMock) as mock_verify,
        patch("engine.pipeline.generate_report", new_callable=AsyncMock) as mock_report,
    ):
        mock_scrape.side_effect = [
            _mock_scrape_result("https://acme.com", "Acme"),
            _mock_scrape_result("https://widget.co", "WidgetCo"),
        ]
        mock_analyze.side_effect = [
            _mock_analysis_result("https://acme.com", "Acme"),
            _mock_analysis_result("https://widget.co", "WidgetCo"),
        ]
        mock_verify.return_value = _mock_verification_output()
        mock_report.return_value = _mock_report_output()

        await run_pipeline(ctx, emitter)

    assert mock_scrape.call_count == 2
    assert mock_analyze.call_count == 2


@pytest.mark.asyncio
async def test_pipeline_state_transitions():
    """Pipeline should transition through all states."""
    ctx = _make_ctx()
    emitter = InMemoryEmitter()

    states_observed: list[PipelineState] = []

    original_emit = emitter.emit

    async def tracking_emit(event: AgentEvent) -> None:
        states_observed.append(ctx.state)
        await original_emit(event)

    emitter.emit = tracking_emit

    with (
        patch("engine.pipeline.scrape_competitor", new_callable=AsyncMock) as mock_scrape,
        patch("engine.pipeline.analyze_competitor", new_callable=AsyncMock) as mock_analyze,
        patch("engine.pipeline.verify_claims", new_callable=AsyncMock) as mock_verify,
        patch("engine.pipeline.generate_report", new_callable=AsyncMock) as mock_report,
    ):
        mock_scrape.return_value = _mock_scrape_result()
        mock_analyze.return_value = _mock_analysis_result()
        mock_verify.return_value = _mock_verification_output()
        mock_report.return_value = _mock_report_output()

        await run_pipeline(ctx, emitter)

    assert PipelineState.SCRAPING in states_observed
    assert PipelineState.ANALYZING in states_observed
    assert PipelineState.VERIFYING in states_observed
    assert PipelineState.REPORTING in states_observed
    assert ctx.state == PipelineState.DONE
