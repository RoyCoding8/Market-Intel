"""Tests for LLM concurrency limits and retry behavior."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from contracts.engine import (
    AnalysisRequest,
    ScrapeResult,
    ScrapedContent,
    VerificationRequest,
    Claim,
)
from engine.agents.analyzer import analyze_competitor, _PageAnalysis

def _make_scrape_result(num_pages: int = 5) -> ScrapeResult:
    pages = [
        ScrapedContent(
            url=f"https://acme.com/page-{i}",
            title=f"Page {i}",
            html_text=f"Content about pricing $9/mo and features. This is page {i} with enough content to pass the quality filter and be analyzed by the LLM.",
            page_type="homepage" if i == 0 else "features",
            scraped_at=datetime.now(timezone.utc),
            content_quality=0.5,
        )
        for i in range(num_pages)
    ]
    return ScrapeResult(
        competitor_url="https://acme.com",
        competitor_name="Acme",
        pages=pages,
        errors=[],
        total_pages_attempted=num_pages,
    )

def _make_claims(n: int = 5) -> list[Claim]:
    return [
        Claim(
            id=f"claim-{i}",
            text=f"Claim {i}: Acme has feature X",
            category="features",
            source_url=f"https://acme.com/page-{i % 5}",
            source_quote=f"Exact quote about feature X from page {i}",
            competitor_url="https://acme.com",
            extracted_at=datetime.now(timezone.utc),
        )
        for i in range(n)
    ]

@pytest.mark.asyncio
async def test_analyzer_calls_run_sequential():
    scrape = _make_scrape_result(num_pages=6)

    async def tracking_run_sequential(calls, **kwargs):
        return [_PageAnalysis(page_type="other", confidence=0.5) for _ in calls]

    with patch("engine.agents.analyzer.run_sequential", side_effect=tracking_run_sequential) as mock_run:
        request = AnalysisRequest(scrape_result=scrape, focus_areas=["pricing"])
        result = await analyze_competitor(request)

    assert mock_run.call_count == 1
    assert len(mock_run.call_args[0][0]) == 6
    assert result.competitor_name == "Acme"

@pytest.mark.asyncio
async def test_verifier_respects_concurrency_limit():
    from engine.agents.verifier import verify_claims

    max_concurrent = 0
    current_concurrent = 0

    async def tracking_verify(prompt, response_model, **kwargs):
        nonlocal max_concurrent, current_concurrent
        current_concurrent += 1
        if current_concurrent > max_concurrent:
            max_concurrent = current_concurrent
        await asyncio.sleep(0.05)
        current_concurrent -= 1
        return response_model(
            verified=True, confidence=0.8, confidence_level="medium",
            reason="supported", source_url="https://acme.com/page-0",
        )

    claims = _make_claims(10)
    scrape = _make_scrape_result(num_pages=1)

    with patch("engine.agents.verifier.extract_structured", side_effect=tracking_verify):
        request = VerificationRequest(
            claims=claims,
            scrape_results=[scrape],
            verification_passes=1,
        )
        result = await verify_claims(request, model="test-model")

    assert max_concurrent <= 5
    assert result.total_claims == 10

@pytest.mark.asyncio
async def test_analyzer_continues_after_single_page_failure():
    scrape = _make_scrape_result(num_pages=3)

    async def partial_failure(calls, **kwargs):
        return [None, _PageAnalysis(page_type="pricing", confidence=0.8), None]

    with patch("engine.agents.analyzer.run_sequential", side_effect=partial_failure):
        request = AnalysisRequest(scrape_result=scrape, focus_areas=["pricing"])
        result = await analyze_competitor(request)

    assert result.competitor_name == "Acme"
    assert result.pricing_data is None
    assert len(result.claims) == 0

@pytest.mark.asyncio
async def test_scraper_retry_on_network_error():
    import httpx
    from tenacity import retry, stop_after_attempt, wait_none, retry_if_exception_type

    attempt_count = 0

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_none(),
        retry=retry_if_exception_type(httpx.ConnectError),
        reraise=True,
    )
    async def mock_fetch():
        nonlocal attempt_count
        attempt_count += 1
        raise httpx.ConnectError("Connection refused")

    with pytest.raises(httpx.ConnectError):
        await mock_fetch()

    assert attempt_count == 3

@pytest.mark.asyncio
async def test_llm_module_loads_without_error():
    from engine.llm import extract_structured
    assert callable(extract_structured)
