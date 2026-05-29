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
    _PricingExtraction,
    _FeatureExtraction,
    _TeamExtraction,
    _NewsExtraction,
    _ClaimExtraction,
    _ClaimItem,
    _FeatureItem,
    _NewsItem,
    _PricingPlan,
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
                html_text="Acme Corp builds widgets. Pricing: $9/mo Starter, $29/mo Pro.",
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


@pytest.mark.asyncio
async def test_analyze_competitor_extracts_claims():
    """Analyzer should extract claims from scraped pages."""
    scrape = _make_scrape_result()

    mock_claim = _ClaimItem(
        text="Acme offers a $9/mo Starter plan",
        category="pricing",
        source_quote="Pricing: $9/mo Starter",
    )

    with patch("engine.agents.analyzer.extract_structured", new_callable=AsyncMock) as mock_llm:
        # Set up return values for each extraction type
        async def side_effect(prompt, model_cls, **kwargs):
            if model_cls is _PricingExtraction:
                return _PricingExtraction(
                    plans=[_PricingPlan(name="Starter", price="$9/mo")],
                    has_free_tier=False,
                )
            if model_cls is _FeatureExtraction:
                return _FeatureExtraction(features=[])
            if model_cls is _TeamExtraction:
                return _TeamExtraction(team_size="10-50")
            if model_cls is _NewsExtraction:
                return _NewsExtraction(items=[])
            if model_cls is _ClaimExtraction:
                return _ClaimExtraction(claims=[mock_claim])
            return None

        mock_llm.side_effect = side_effect

        result = await analyze_competitor(
            AnalysisRequest(scrape_result=scrape),
            model="test-model",
        )

    assert result.competitor_name == "Acme"
    assert len(result.claims) >= 1
    assert result.claims[0].text == "Acme offers a $9/mo Starter plan"
    assert result.claims[0].category == "pricing"
    assert result.pricing_data is not None
    assert result.team_data is not None


@pytest.mark.asyncio
async def test_analyze_competitor_skips_non_pricing_pages():
    """Blog pages should skip pricing extraction but still extract news and claims."""
    pages = [
        ScrapedContent(
            url="https://acme.com/blog/post-1",
            title="Blog Post",
            html_text="Some blog content about widgets.",
            page_type="blog",
            scraped_at=datetime.now(timezone.utc),
            content_quality=0.5,
        ),
    ]
    scrape = _make_scrape_result(pages=pages)

    with patch("engine.agents.analyzer.extract_structured", new_callable=AsyncMock) as mock_llm:
        async def side_effect(prompt, model_cls, **kwargs):
            # Blog pages only trigger: features, team, news, claims
            # Pricing is skipped because blog is not in the pricing page types
            if model_cls is _FeatureExtraction:
                return _FeatureExtraction(features=[])
            if model_cls is _TeamExtraction:
                return _TeamExtraction()
            if model_cls is _NewsExtraction:
                return _NewsExtraction(items=[_NewsItem(title="New release", source="blog")])
            if model_cls is _ClaimExtraction:
                return _ClaimExtraction(claims=[])
            return None

        mock_llm.side_effect = side_effect

        result = await analyze_competitor(
            AnalysisRequest(scrape_result=scrape),
            model="test-model",
        )

    # Pricing extraction was skipped (blog page type), so no pricing data
    assert result.pricing_data is None
    # News was extracted from blog page
    assert len(result.news_data) >= 1
    # Pricing extraction was never called
    pricing_calls = [c for c in mock_llm.call_args_list if c[0][1] is _PricingExtraction]
    assert len(pricing_calls) == 0


@pytest.mark.asyncio
async def test_analyze_competitor_handles_llm_failure():
    """Analyzer should handle LLM failures gracefully per-page."""
    scrape = _make_scrape_result()

    with patch("engine.agents.analyzer.extract_structured", new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = Exception("LLM API error")

        result = await analyze_competitor(
            AnalysisRequest(scrape_result=scrape),
            model="test-model",
        )

    # Should not crash, just return empty results
    assert result.competitor_name == "Acme"
    assert result.claims == []
    assert result.pricing_data is None


@pytest.mark.asyncio
async def test_analyze_competitor_merges_multiple_pages():
    """Multiple pages should be analyzed and results merged."""
    pages = [
        ScrapedContent(
            url="https://acme.com",
            title="Home",
            html_text="Welcome to Acme",
            page_type="homepage",
            scraped_at=datetime.now(timezone.utc),
            content_quality=0.5,
        ),
        ScrapedContent(
            url="https://acme.com/features",
            title="Features",
            html_text="Widget automation, AI-powered analytics",
            page_type="features",
            scraped_at=datetime.now(timezone.utc),
            content_quality=0.5,
        ),
    ]
    scrape = _make_scrape_result(pages=pages)

    call_count = 0

    with patch("engine.agents.analyzer.extract_structured", new_callable=AsyncMock) as mock_llm:
        async def side_effect(prompt, model_cls, **kwargs):
            nonlocal call_count
            call_count += 1
            if model_cls is _PricingExtraction:
                return _PricingExtraction(plans=[_PricingPlan(name="Pro", price="$29/mo")])
            if model_cls is _FeatureExtraction:
                return _FeatureExtraction(
                    features=[_FeatureItem(name="Automation", category="Core")]
                )
            if model_cls is _TeamExtraction:
                return _TeamExtraction()
            if model_cls is _NewsExtraction:
                return _NewsExtraction()
            if model_cls is _ClaimExtraction:
                return _ClaimExtraction(claims=[])
            return None

        mock_llm.side_effect = side_effect

        result = await analyze_competitor(
            AnalysisRequest(scrape_result=scrape),
            model="test-model",
        )

    # Homepage gets all 5 extraction types, features page gets 3 (pricing + features + claims)
    assert call_count == 8
    assert len(result.features_data) >= 1
