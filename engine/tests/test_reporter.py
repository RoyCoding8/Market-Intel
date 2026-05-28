"""Tests for the reporter agent."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from contracts.engine import (
    AnalysisResult,
    Claim,
    ReportRequest,
    VerificationOutput,
    VerificationResult,
)
from engine.agents.reporter import (
    _ReportDraft,
    _Finding,
    _Citation,
    _ComparisonTable,
    _ComparisonRow,
    _build_analysis_summary,
    _build_verification_summary,
    generate_report,
)


# ---------------------------------------------------------------------------
# Unit tests — helpers
# ---------------------------------------------------------------------------


class TestBuildAnalysisSummary:
    def test_includes_competitor_name(self):
        ar = AnalysisResult(
            competitor_url="https://acme.com",
            competitor_name="Acme",
            claims=[],
        )
        result = _build_analysis_summary([ar])
        assert "Acme" in result

    def test_includes_pricing_data(self):
        ar = AnalysisResult(
            competitor_url="https://acme.com",
            competitor_name="Acme",
            claims=[],
            pricing_data={"plans": [{"name": "Pro", "price": "$29/mo"}]},
        )
        result = _build_analysis_summary([ar])
        assert "$29" in result

    def test_includes_claims(self):
        ar = AnalysisResult(
            competitor_url="https://acme.com",
            competitor_name="Acme",
            claims=[
                Claim(
                    id="c1",
                    text="Acme has a free tier",
                    category="pricing",
                    source_url="https://acme.com",
                    source_quote="Free plan available",
                    competitor_url="https://acme.com",
                    extracted_at=datetime.now(timezone.utc),
                ),
            ],
        )
        result = _build_analysis_summary([ar])
        assert "free tier" in result.lower()


class TestBuildVerificationSummary:
    def test_includes_counts(self):
        vo = VerificationOutput(
            results=[],
            total_claims=10,
            verified_count=7,
            flagged_count=3,
            passes_completed=2,
        )
        result = _build_verification_summary(vo)
        assert "10" in result
        assert "7" in result
        assert "3" in result

    def test_includes_flagged_details(self):
        vo = VerificationOutput(
            results=[
                VerificationResult(
                    claim_id="c1",
                    verified=False,
                    confidence=0.2,
                    confidence_level="low",
                    reason="Unsupported claim",
                    source_url="https://example.com",
                ),
            ],
            total_claims=1,
            verified_count=0,
            flagged_count=1,
            passes_completed=2,
        )
        result = _build_verification_summary(vo)
        assert "Flagged claims" in result
        assert "Unsupported" in result


# ---------------------------------------------------------------------------
# Integration tests — generate_report
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_report_basic():
    """Report generation should produce structured output."""
    ar = AnalysisResult(
        competitor_url="https://acme.com",
        competitor_name="Acme",
        claims=[
            Claim(
                id="c1",
                text="Acme has a free tier",
                category="pricing",
                source_url="https://acme.com/pricing",
                source_quote="Free plan available",
                competitor_url="https://acme.com",
                extracted_at=datetime.now(timezone.utc),
            ),
        ],
    )
    vo = VerificationOutput(
        results=[
            VerificationResult(
                claim_id="c1",
                verified=True,
                confidence=0.9,
                confidence_level="high",
                reason="Supported",
                supporting_quote="Free plan available",
                source_url="https://acme.com/pricing",
            ),
        ],
        total_claims=1,
        verified_count=1,
        flagged_count=0,
        passes_completed=2,
    )

    mock_draft = _ReportDraft(
        executive_summary="Acme Corp offers competitive pricing with a free tier.",
        findings=[
            _Finding(
                title="Free Tier Available",
                summary="Acme offers a free tier with basic features.",
                category="pricing",
                confidence="high",
                confidence_score=0.9,
                citations=[
                    _Citation(
                        url="https://acme.com/pricing",
                        quote="Free plan available",
                        page_type="pricing",
                    ),
                ],
                impact="high",
                recommendation="Consider matching their free tier offering.",
            ),
        ],
        comparison_tables=[
            _ComparisonTable(
                title="Pricing Comparison",
                rows=[
                    _ComparisonRow(
                        dimension="Free Tier",
                        values={"Acme": "Yes"},
                        winner="Acme",
                    ),
                ],
            ),
        ],
        recommendations=["Launch a free tier to compete with Acme"],
    )

    with patch("engine.agents.reporter.extract_structured", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_draft

        result = await generate_report(
            ReportRequest(analysis_results=[ar], verification_output=vo, query="Compare pricing"),
            model="test-model",
        )

    assert "Acme" in result.executive_summary
    assert len(result.findings) == 1
    assert result.findings[0]["citations"][0]["url"] == "https://acme.com/pricing"
    assert len(result.comparison_tables) == 1
    assert len(result.recommendations) >= 1
    assert result.total_sources == 1


@pytest.mark.asyncio
async def test_generate_report_handles_llm_failure():
    """Report generation should return a minimal report on LLM failure."""
    ar = AnalysisResult(
        competitor_url="https://acme.com",
        competitor_name="Acme",
        claims=[],
    )
    vo = VerificationOutput(
        results=[], total_claims=0, verified_count=0, flagged_count=0, passes_completed=0
    )

    with patch("engine.agents.reporter.extract_structured", new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = Exception("LLM failure")

        result = await generate_report(
            ReportRequest(analysis_results=[ar], verification_output=vo),
            model="test-model",
        )

    assert "failed" in result.executive_summary.lower()
    assert result.findings == []


@pytest.mark.asyncio
async def test_generate_report_multiple_competitors():
    """Report should handle multiple competitors."""
    ar1 = AnalysisResult(
        competitor_url="https://acme.com",
        competitor_name="Acme",
        claims=[],
        pricing_data={"plans": [{"name": "Pro", "price": "$29/mo"}]},
    )
    ar2 = AnalysisResult(
        competitor_url="https://widget.co",
        competitor_name="WidgetCo",
        claims=[],
        pricing_data={"plans": [{"name": "Business", "price": "$49/mo"}]},
    )
    vo = VerificationOutput(
        results=[], total_claims=0, verified_count=0, flagged_count=0, passes_completed=1
    )

    mock_draft = _ReportDraft(
        executive_summary="Acme and WidgetCo comparison shows different pricing strategies.",
        findings=[],
        comparison_tables=[
            _ComparisonTable(
                title="Pricing",
                rows=[
                    _ComparisonRow(dimension="Price", values={"Acme": "$29", "WidgetCo": "$49"}),
                ],
            ),
        ],
        recommendations=["Compete on price"],
    )

    with patch("engine.agents.reporter.extract_structured", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_draft

        result = await generate_report(
            ReportRequest(analysis_results=[ar1, ar2], verification_output=vo),
            model="test-model",
        )

    assert "Acme" in result.executive_summary
    assert "WidgetCo" in result.executive_summary
    assert result.total_sources == 0  # No claims
