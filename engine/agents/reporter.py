"""Reporter agent — generates the final intelligence report with citations (v2)."""

from __future__ import annotations

import logging
from typing import Optional

from pydantic import BaseModel, Field

from contracts.engine import AnalysisResult, ReportOutput, ReportRequest, VerificationOutput
from engine.llm import extract_structured

logger = logging.getLogger(__name__)

# ── Internal extraction models ────────────────────────────────────────────

class _Citation(BaseModel):
    url: str
    quote: str
    page_type: str = "unknown"

class _Finding(BaseModel):
    title: str
    summary: str
    category: str
    confidence: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    citations: list[_Citation] = Field(default_factory=list)
    impact: Optional[str] = None
    recommendation: Optional[str] = None

class _ComparisonRow(BaseModel):
    dimension: str
    values: dict[str, str]
    winner: Optional[str] = None

class _ComparisonTable(BaseModel):
    title: str
    rows: list[_ComparisonRow] = Field(default_factory=list)

class _ReportDraft(BaseModel):
    executive_summary: str
    findings: list[_Finding] = Field(default_factory=list)
    comparison_tables: list[_ComparisonTable] = Field(default_factory=list)
    trend_analysis: Optional[str] = None
    recommendations: list[str] = Field(default_factory=list)
    immediate_actions: list[str] = Field(default_factory=list)
    short_term_actions: list[str] = Field(default_factory=list)
    strategic_considerations: list[str] = Field(default_factory=list)


# ── Prompt ────────────────────────────────────────────────────────────────

_REPORT_PROMPT = """You are a senior intelligence analyst generating a competitor analysis report.

## Analysis Data
{analysis_summary}

## Verification Summary
{verification_summary}

## Original Query
{query}

Generate a comprehensive competitive intelligence report. Structure it as:

1. EXECUTIVE SUMMARY (2-3 paragraphs)
   - Key findings overview
   - Strategic implications
   - Recommended actions

2. FINDINGS (each with):
   - Clear, actionable title
   - Detailed summary (3-5 sentences)
   - Impact assessment (high/medium/low with reasoning)
   - Specific recommendation
   - Full citation chain

3. COMPARISON TABLES:
   - Pricing comparison
   - Feature comparison
   - Market position comparison
   - Team/growth comparison

4. TREND ANALYSIS:
   - What patterns emerge from the data?
   - What are competitors investing in?
   - Where are the gaps?

5. RECOMMENDATIONS (prioritized):
   - Immediate actions (this week)
   - Short-term actions (this month)
   - Strategic considerations (this quarter)

Every finding MUST include at least one citation with a URL and an exact source quote.
Focus on actionable intelligence, not generic observations."""


# ── Helpers ───────────────────────────────────────────────────────────────

def _build_analysis_summary(analysis_results: list[AnalysisResult]) -> str:
    parts: list[str] = []
    for ar in analysis_results:
        part = f"### {ar.competitor_name} ({ar.competitor_url})\n"
        if ar.pricing_data:
            part += "Pricing:\n" + "\n".join(
                f"  - {p.get('name', '?')}: {p.get('price', 'N/A')}"
                for p in ar.pricing_data.get("plans", [])
            ) + "\n"
        if ar.features_data:
            part += f"Features: {len(ar.features_data)} found\n"
            for f in ar.features_data[:5]:
                part += f"  - {f.get('name', '?')}: {f.get('description', '')[:100]}\n"
        if ar.team_data:
            part += f"Team: {ar.team_data.get('team_size', 'unknown')}\n"
        if ar.news_data:
            part += f"News: {len(ar.news_data)} items\n"
        if ar.claims:
            part += f"Claims: {len(ar.claims)} extracted\n"
            for c in ar.claims[:5]:
                part += f"  - [{c.category}] {c.text[:120]}\n"
        parts.append(part)
    return "\n".join(parts)


def _build_verification_summary(
    verification: VerificationOutput,
    analysis_results: list[AnalysisResult] | None = None,
) -> str:
    claim_map = {
        claim.id: claim
        for analysis in (analysis_results or [])
        for claim in analysis.claims
    }
    lines = [
        f"Total claims: {verification.total_claims}",
        f"Verified: {verification.verified_count}",
        f"Flagged: {verification.flagged_count}",
        f"Passes completed: {verification.passes_completed}",
    ]
    verified = [r for r in verification.results if r.verified]
    if verified:
        lines.append("\nVerified source-backed claims:")
        for r in verified[:50]:
            claim = claim_map.get(r.claim_id)
            quote = r.supporting_quote or (claim.source_quote if claim else "")
            claim_text = claim.text if claim else r.claim_id
            lines.append(
                f"  - {claim_text}\n"
                f"    URL: {r.source_url}\n"
                f"    Quote: {quote[:500]}\n"
                f"    Confidence: {r.confidence:.2f} ({r.confidence_level})"
            )
    flagged = [r for r in verification.results if not r.verified]
    if flagged:
        lines.append("\nFlagged claims:")
        for r in flagged[:10]:
            concerns = f" [Concerns: {', '.join(r.concerns)}]" if r.concerns else ""
            lines.append(f"  - {r.claim_id}: {r.reason[:100]} (confidence: {r.confidence}){concerns}")
    return "\n".join(lines)


def _fallback_report(request: ReportRequest, reason: str) -> ReportOutput:
    claims = {
        claim.id: claim
        for analysis in request.analysis_results
        for claim in analysis.claims
    }
    findings = []
    # If verification produced no results (e.g., verification failed), include all claims
    results_to_use = [r for r in request.verification_output.results if r.verified]
    if not results_to_use and claims:
        # Verification failed or produced nothing — include all claims as unverified
        for i, claim in enumerate(claims.values(), 1):
            findings.append({
                "title": claim.text[:90],
                "summary": claim.text,
                "category": claim.category,
                "confidence": "low",
                "confidence_score": 0.3,
                "citations": [{"url": claim.source_url, "quote": claim.source_quote, "page_type": "source"}],
                "impact": "Unverified competitor signal.",
                "recommendation": "Verify this claim before acting on it.",
            })
        return ReportOutput(
            executive_summary=f"Generated fallback report (unverified claims) because {reason}.",
            findings=findings,
            comparison_tables=[],
            recommendations=["These claims were not verified. Review sources before acting."],
            total_sources=len({c.source_url for ar in request.analysis_results for c in ar.claims}),
        )
    for i, result in enumerate(results_to_use, 1):
        claim = claims.get(result.claim_id)
        title = claim.text[:90] if claim else f"Verified claim {i}"
        quote = result.supporting_quote or (claim.source_quote if claim else "")
        findings.append({
            "title": title,
            "summary": claim.text if claim else result.reason,
            "category": claim.category if claim else "general",
            "confidence": result.confidence_level,
            "confidence_score": result.confidence,
            "citations": [{"url": result.source_url, "quote": quote, "page_type": "source"}],
            "impact": "Source-backed competitor signal.",
            "recommendation": "Review this verified signal for positioning, pricing, or product-response opportunities.",
        })
    return ReportOutput(
        executive_summary=f"Generated a source-backed fallback report because {reason}.",
        findings=findings,
        comparison_tables=[],
        recommendations=["Review verified claims with citations before acting."],
        total_sources=len({c.source_url for ar in request.analysis_results for c in ar.claims}),
    )


# ── Public API ────────────────────────────────────────────────────────────

async def generate_report(
    request: ReportRequest,
    model: str = "openai/mimo-v2.5-pro",
) -> ReportOutput:
    """Generate a structured intelligence report from analysis and verification results."""
    prompt = _REPORT_PROMPT.format(
        analysis_summary=_build_analysis_summary(request.analysis_results),
        verification_summary=_build_verification_summary(
            request.verification_output,
            request.analysis_results,
        ),
        query=request.query or "General competitor intelligence",
    )

    try:
        draft = await extract_structured(prompt, _ReportDraft, model=model)
    except Exception as exc:
        logger.error("Report generation LLM call failed: %s", exc)
        return _fallback_report(request, "LLM report generation failed")

    findings = [
        {"title": f.title, "summary": f.summary, "category": f.category,
         "confidence": f.confidence, "confidence_score": f.confidence_score,
         "citations": [c.model_dump() for c in f.citations],
         "impact": f.impact, "recommendation": f.recommendation}
        for f in draft.findings
    ]
    if not findings and request.verification_output.verified_count:
        return _fallback_report(request, "the report draft contained no findings")

    all_recommendations = list(draft.recommendations)
    for label, actions in [
        ("Immediate Actions (this week)", draft.immediate_actions),
        ("Short-term Actions (this month)", draft.short_term_actions),
        ("Strategic Considerations (this quarter)", draft.strategic_considerations),
    ]:
        if actions:
            all_recommendations.append(f"--- {label} ---")
            all_recommendations.extend(actions)

    total_sources = len({c.source_url for ar in request.analysis_results for c in ar.claims})
    logger.info("Report generated: %d findings, %d comparison tables, %d sources",
                len(findings), len(draft.comparison_tables), total_sources)

    return ReportOutput(
        executive_summary=draft.executive_summary, findings=findings,
        comparison_tables=[{"title": t.title, "rows": [r.model_dump() for r in t.rows]}
                          for t in draft.comparison_tables],
        trend_analysis=draft.trend_analysis, recommendations=all_recommendations,
        total_sources=total_sources,
    )
