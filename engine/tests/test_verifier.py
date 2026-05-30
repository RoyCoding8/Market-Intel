"""Tests for the verifier agent."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from contracts.engine import (
    Claim,
    ScrapeResult,
    ScrapedContent,
    VerificationRequest,
)
from engine.agents.verifier import (
    _VerificationJudgement,
    _find_source_text,
    _confidence_level,
    verify_claims,
)

# ---------------------------------------------------------------------------
# Unit tests — helpers
# ---------------------------------------------------------------------------

class TestConfidenceLevel:
    def test_high(self):
        assert _confidence_level(0.9) == "high"

    def test_medium(self):
        assert _confidence_level(0.7) == "medium"

    def test_low(self):
        assert _confidence_level(0.3) == "very_low"

    def test_boundary_high(self):
        assert _confidence_level(0.8) == "medium"

    def test_boundary_medium(self):
        assert _confidence_level(0.6) == "low"

class TestFindSourceText:
    def test_finds_exact_url(self):
        claim = Claim(
            id="c1",
            text="Acme has 100 employees",
            category="talent",
            source_url="https://acme.com/about",
            source_quote="Team of 100",
            competitor_url="https://acme.com",
            extracted_at=datetime.now(timezone.utc),
        )
        scrape = ScrapeResult(
            competitor_url="https://acme.com",
            pages=[
                ScrapedContent(
                    url="https://acme.com/about",
                    title="About",
                    html_text="We are a team of 100 engineers.",
                    page_type="about",
                    scraped_at=datetime.now(timezone.utc),
                ),
            ],
        )
        result = _find_source_text(claim, [scrape])
        assert "team of 100" in result

    def test_falls_back_to_competitor_url(self):
        claim = Claim(
            id="c2",
            text="Acme costs $9",
            category="pricing",
            source_url="https://acme.com/pricing-page",
            source_quote="$9/mo",
            competitor_url="https://acme.com",
            extracted_at=datetime.now(timezone.utc),
        )
        scrape = ScrapeResult(
            competitor_url="https://acme.com",
            pages=[
                ScrapedContent(
                    url="https://acme.com",
                    title="Home",
                    html_text="Pricing starts at $9/mo for our Starter plan.",
                    page_type="homepage",
                    scraped_at=datetime.now(timezone.utc),
                ),
            ],
        )
        result = _find_source_text(claim, [scrape])
        assert "$9" in result

    def test_returns_not_found_message(self):
        claim = Claim(
            id="c3",
            text="X",
            category="feature",
            source_url="https://other.com",
            source_quote="Q",
            competitor_url="https://other.com",
            extracted_at=datetime.now(timezone.utc),
        )
        result = _find_source_text(claim, [])
        assert "not found" in result.lower()

# ---------------------------------------------------------------------------
# Integration tests — verify_claims
# ---------------------------------------------------------------------------

def _make_test_claim(
    claim_id: str = "claim-1",
    text: str = "Acme offers a free tier",
    source_url: str = "https://acme.com/pricing",
    source_quote: str = "Free plan available",
) -> Claim:
    return Claim(
        id=claim_id,
        text=text,
        category="pricing",
        source_url=source_url,
        source_quote=source_quote,
        competitor_url="https://acme.com",
        extracted_at=datetime.now(timezone.utc),
    )

def _make_test_scrape_result() -> ScrapeResult:
    return ScrapeResult(
        competitor_url="https://acme.com",
        competitor_name="Acme",
        pages=[
            ScrapedContent(
                url="https://acme.com/pricing",
                title="Pricing",
                html_text="Acme offers a free tier with basic features. Pro plan is $29/mo.",
                page_type="pricing",
                scraped_at=datetime.now(timezone.utc),
            ),
        ],
    )

@pytest.mark.asyncio
async def test_verify_claims_confirmed():
    """High-confidence verification should mark claim as verified."""
    claim = _make_test_claim()
    scrape = _make_test_scrape_result()

    with patch("engine.agents.verifier.extract_structured", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = _VerificationJudgement(
            verified=True,
            confidence=0.95,
            confidence_level="high",
            reason="Source clearly states free tier is available.",
            supporting_quote="Acme offers a free tier with basic features.",
        )

        result = await verify_claims(
            VerificationRequest(claims=[claim], scrape_results=[scrape]),
            model="test-model",
        )

    assert result.total_claims == 1
    assert result.verified_count == 1
    assert result.flagged_count == 0
    assert result.results[0].verified is True
    assert result.results[0].confidence >= 0.8
    assert result.results[0].confidence_level == "high"

@pytest.mark.asyncio
async def test_verify_claims_flagged():
    """Low-confidence verification should flag the claim."""
    claim = _make_test_claim(text="Acme has 10,000 employees")

    with patch("engine.agents.verifier.extract_structured", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = _VerificationJudgement(
            verified=False,
            confidence=0.2,
            confidence_level="very_low",
            reason="Source does not mention employee count.",
            supporting_quote=None,
        )

        result = await verify_claims(
            VerificationRequest(claims=[claim], scrape_results=[_make_test_scrape_result()]),
            model="test-model",
        )

    assert result.verified_count == 0
    assert result.flagged_count == 1
    assert result.results[0].verified is False

@pytest.mark.asyncio
async def test_verify_claims_rejects_hallucinated_quote():
    """LLM says verified but supporting quote is NOT in source text → must be flagged."""
    claim = _make_test_claim()
    scrape = _make_test_scrape_result()

    with patch("engine.agents.verifier.extract_structured", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = _VerificationJudgement(
            verified=True,
            confidence=0.9,
            confidence_level="high",
            reason="Supported.",
            supporting_quote="This quote does not appear anywhere in the scraped source text at all.",
        )

        result = await verify_claims(
            VerificationRequest(claims=[claim], scrape_results=[scrape]),
            model="test-model",
        )

    assert result.results[0].verified is False
    assert result.results[0].confidence <= 0.49
    assert any("quote" in c.lower() for c in result.results[0].concerns)
    assert result.results[0].confidence_level == "very_low"

@pytest.mark.asyncio
async def test_verify_claims_handles_llm_failure():
    """LLM failures should produce flagged claims with zero confidence."""
    claim = _make_test_claim()

    with patch("engine.agents.verifier.extract_structured", new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = Exception("API timeout")

        result = await verify_claims(
            VerificationRequest(claims=[claim], scrape_results=[_make_test_scrape_result()]),
            model="test-model",
        )

    assert result.total_claims == 1
    assert result.results[0].verified is False
    assert result.results[0].confidence == 0.0

@pytest.mark.asyncio
async def test_verify_claims_multiple():
    """Multiple claims should all be verified independently."""
    claims = [
        _make_test_claim(claim_id="c1", text="Free tier exists"),
        _make_test_claim(claim_id="c2", text="Pro is $29/mo"),
        _make_test_claim(claim_id="c3", text="Acme has AI features"),
    ]

    call_count = 0

    with patch("engine.agents.verifier.extract_structured", new_callable=AsyncMock) as mock_llm:
        async def side_effect(prompt, model_cls, **kwargs):
            nonlocal call_count
            call_count += 1
            return _VerificationJudgement(
                verified=True,
                confidence=0.85,
                confidence_level="high",
                reason="Supported by source.",
                supporting_quote="Acme offers a free tier with basic features.",
            )

        mock_llm.side_effect = side_effect

        result = await verify_claims(
            VerificationRequest(claims=claims, scrape_results=[_make_test_scrape_result()]),
            model="test-model",
        )

    assert result.total_claims == 3
    assert result.verified_count == 3
    assert call_count == 3  # One call per claim
