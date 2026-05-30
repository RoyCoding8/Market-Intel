"""Tests for the analyzer agent."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from contracts.engine import (
    AnalysisRequest,
    ScrapeResult,
    ScrapedContent,
)
from engine.agents.analyzer import (
    _PageAnalysis,
    _PricingData,
    _PricingPlan,
    _FeatureItem,
    _TeamData,
    _NewsItem,
    _ClaimItem,
    analyze_competitor,
)

def _make_scrape_result(
    pages: list[ScrapedContent] | None = None,
    competitor_url: str = "https://acme.com",
    competitor_name: str = "Acme",
) -> ScrapeResult:
    if pages is None:
        pages = [
            ScrapedContent(
                url="https://acme.com",
                title="Acme Corp",
                html_text="Acme Corp builds widgets for enterprise teams. Pricing: $9/mo Starter plan with basic features, $29/mo Pro plan with advanced analytics and priority support.",
                page_type="homepage",
                scraped_at=datetime.now(timezone.utc),
                content_quality=0.5,
            ),
        ]
    return ScrapeResult(
        competitor_url=competitor_url,
        competitor_name=competitor_name,
        pages=pages,
        errors=[],
        total_pages_attempted=len(pages),
    )

def _make_analysis(
    page_type: str = "pricing",
    pricing: _PricingData | None = None,
    features: list[_FeatureItem] | None = None,
    team: _TeamData | None = None,
    news: list[_NewsItem] | None = None,
    claims: list[_ClaimItem] | None = None,
    confidence: float = 0.9,
) -> _PageAnalysis:
    return _PageAnalysis(
        page_type=page_type,
        confidence=confidence,
        pricing=pricing,
        features=features or [],
        team=team,
        news=news or [],
        claims=claims or [],
    )

@pytest.mark.asyncio
async def test_analyze_competitor_extracts_claims():
    scrape = _make_scrape_result()
    mock_claim = _ClaimItem(
        text="Acme offers a $9/mo Starter plan",
        category="pricing",
        source_quote="Pricing: $9/mo Starter",
    )

    with patch("engine.agents.analyzer.run_sequential", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = [_make_analysis(
            page_type="pricing",
            pricing=_PricingData(plans=[_PricingPlan(name="Starter", price="$9/mo")]),
            claims=[mock_claim],
            confidence=0.85,
        )]
        result = await analyze_competitor(
            AnalysisRequest(scrape_result=scrape), model="test-model",
        )

    assert result.competitor_name == "Acme"
    assert len(result.claims) == 1
    assert result.claims[0].text == "Acme offers a $9/mo Starter plan"
    assert result.claims[0].category == "pricing"
    assert result.claims[0].relevance == 0.85
    assert result.pricing_data is not None
    assert result.pricing_data["plans"][0]["name"] == "Starter"

@pytest.mark.asyncio
async def test_analyze_competitor_skips_low_quality():
    pages = [
        ScrapedContent(
            url="https://acme.com/empty", title="Empty", html_text="x",
            page_type="other", scraped_at=datetime.now(timezone.utc), content_quality=0.05,
        ),
    ]
    scrape = _make_scrape_result(pages=pages)

    with patch("engine.agents.analyzer.run_sequential", new_callable=AsyncMock) as mock_run:
        result = await analyze_competitor(
            AnalysisRequest(scrape_result=scrape), model="test-model",
        )

    assert result.claims == []
    assert result.pricing_data is None
    mock_run.assert_not_called()

@pytest.mark.asyncio
async def test_analyze_competitor_handles_llm_failure():
    scrape = _make_scrape_result()

    with patch("engine.agents.analyzer.run_sequential", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = [None]
        result = await analyze_competitor(
            AnalysisRequest(scrape_result=scrape), model="test-model",
        )

    assert result.competitor_name == "Acme"
    assert result.claims == []
    assert result.pricing_data is None

@pytest.mark.asyncio
async def test_analyze_competitor_merges_multiple_pages():
    pages = [
        ScrapedContent(
            url="https://acme.com", title="Home",
            html_text="Welcome to Acme Corp. We build amazing widgets for enterprise teams. Pricing starts at $9/mo for our Starter plan.",
            page_type="homepage", scraped_at=datetime.now(timezone.utc), content_quality=0.5,
        ),
        ScrapedContent(
            url="https://acme.com/features", title="Features",
            html_text="Widget automation, AI-powered analytics, real-time dashboards, team collaboration tools, API integrations, and custom workflows.",
            page_type="features", scraped_at=datetime.now(timezone.utc), content_quality=0.5,
        ),
    ]
    scrape = _make_scrape_result(pages=pages)

    with patch("engine.agents.analyzer.run_sequential", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = [
            _make_analysis(
                page_type="pricing",
                pricing=_PricingData(plans=[_PricingPlan(name="Pro", price="$29/mo")]),
                features=[_FeatureItem(name="Automation", category="Core")],
            ),
            _make_analysis(
                page_type="pricing",
                pricing=_PricingData(plans=[_PricingPlan(name="Business", price="$49/mo")]),
                features=[_FeatureItem(name="Analytics", category="Core")],
            ),
        ]
        result = await analyze_competitor(
            AnalysisRequest(scrape_result=scrape), model="test-model",
        )

    assert mock_run.call_count == 1
    assert len(result.features_data) == 2
    assert result.pricing_data is not None
    assert result.pricing_data["plans"][0]["name"] == "Pro"

@pytest.mark.asyncio
async def test_analyze_competitor_single_call_per_page():
    pages = [
        ScrapedContent(
            url="https://acme.com/pricing", title="Pricing",
            html_text="Starter plan: $9/mo with basic features. Pro plan: $29/mo with advanced analytics. Enterprise: Custom pricing with dedicated support and SLA.",
            page_type="pricing", scraped_at=datetime.now(timezone.utc), content_quality=0.8,
        ),
    ]
    scrape = _make_scrape_result(pages=pages)

    with patch("engine.agents.analyzer.run_sequential", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = [_make_analysis(
            page_type="pricing",
            pricing=_PricingData(plans=[_PricingPlan(name="Starter", price="$9/mo")]),
            claims=[_ClaimItem(text="Starter plan costs $9/mo", category="pricing", source_quote="Starter: $9/mo")],
        )]
        result = await analyze_competitor(
            AnalysisRequest(scrape_result=scrape), model="test-model",
        )

    assert mock_run.call_count == 1
    assert result.pricing_data is not None
    assert len(result.claims) == 1

@pytest.mark.asyncio
async def test_analyze_competitor_skips_anti_bot():
    pages = [
        ScrapedContent(
            url="https://acme.com", title="Blocked",
            html_text="Checking your browser...",
            page_type="homepage", scraped_at=datetime.now(timezone.utc), content_quality=0.0,
            anti_bot_detected="cloudflare_challenge",
        ),
    ]
    scrape = _make_scrape_result(pages=pages)

    with patch("engine.agents.analyzer.run_sequential", new_callable=AsyncMock) as mock_run:
        result = await analyze_competitor(
            AnalysisRequest(scrape_result=scrape), model="test-model",
        )

    assert result.claims == []
    mock_run.assert_not_called()
