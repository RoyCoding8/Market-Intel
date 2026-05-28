"""Verifier agent — multi-pass claim verification against source text (v2)."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Optional

from pydantic import BaseModel, Field

from contracts.engine import Claim, ScrapeResult, VerificationOutput, VerificationRequest, VerificationResult
from engine.llm import extract_structured

logger = logging.getLogger(__name__)


# ── Internal extraction model ─────────────────────────────────────────────

class _VerificationJudgement(BaseModel):
    verified: bool
    confidence: float = Field(..., ge=0.0, le=1.0)
    confidence_level: str
    reason: str
    supporting_quote: Optional[str] = None
    concerns: list[str] = Field(default_factory=list)
    exact_match: bool = False
    semantic_match: bool = False
    temporal_accuracy: Optional[str] = None


# ── Prompt ────────────────────────────────────────────────────────────────

_VERIFY_PROMPT = """You are a senior fact-checker verifying an intelligence claim against its source text.

CLAIM:
{claim_text}

EXTRACTED SOURCE QUOTE:
{source_quote}

SOURCE URL: {source_url}
SOURCE TEXT:
{source_text}

Verification criteria — evaluate ALL of the following:

1. **Exact match**: Does the claim exactly match the source text?
2. **Semantic match**: Is the claim logically supported by the source?
3. **Context preservation**: Is the claim taken out of context?
4. **Temporal accuracy**: Is the claim about current state (not outdated)?
5. **Specificity**: Is the claim specific enough to be useful?

Confidence scoring guidelines:
- 0.9-1.0: Claim is directly stated with exact quote
- 0.7-0.9: Claim is clearly implied by the source
- 0.5-0.7: Claim is partially supported
- 0.3-0.5: Claim is weakly supported or ambiguous
- 0.0-0.3: Claim is unsupported or contradicted

Instructions:
1. Determine whether the source text supports, contradicts, or is neutral on the claim.
2. Provide a confidence score following the scale above.
3. Set verified=True if confidence >= 0.5, False otherwise.
4. If supported, extract the exact quote that backs the claim.
5. List any concerns (out-of-context, outdated, vague, etc.)
6. Be conservative — prefer flagging over false verification."""


# ── Helpers ───────────────────────────────────────────────────────────────

def _confidence_level(score: float) -> str:
    if score >= 0.9: return "high"
    if score >= 0.7: return "medium"
    if score >= 0.5: return "low"
    return "very_low"


def _find_source_text(claim: Claim, scrape_results: list[ScrapeResult]) -> str:
    for result in scrape_results:
        for page in result.pages:
            if page.url == claim.source_url:
                return page.html_text[:10000]
    for result in scrape_results:
        if claim.competitor_url == result.competitor_url:
            longest = max(result.pages, key=lambda p: len(p.html_text), default=None)
            if longest:
                return longest.html_text[:10000]
    return "[Source text not found in scrape results]"


_MIN_QUOTE_LENGTH = 20  # minimum characters for a quote to be considered meaningful


def _quote_in_text(quote: str | None, text: str) -> bool:
    if not quote:
        return False
    norm_quote = re.sub(r"\s+", " ", quote).strip().lower()
    norm_text = re.sub(r"\s+", " ", text).lower()
    return len(norm_quote) >= _MIN_QUOTE_LENGTH and norm_quote in norm_text


async def _verify_single_claim(claim: Claim, source_text: str, model: str) -> VerificationResult:
    if source_text.startswith("[Source text not found"):
        return VerificationResult(
            claim_id=claim.id, verified=False, confidence=0.0, confidence_level="very_low",
            reason="Source text was not available for verification.", supporting_quote=None,
            source_url=claim.source_url, concerns=["Source text missing"],
        )

    prompt = _VERIFY_PROMPT.format(
        claim_text=claim.text, source_quote=claim.source_quote,
        source_url=claim.source_url, source_text=source_text[:6000],
    )
    try:
        j = await extract_structured(prompt, _VerificationJudgement, model=model)
    except Exception as exc:
        logger.warning("Verification LLM call failed for claim %s: %s", claim.id, exc)
        return VerificationResult(
            claim_id=claim.id, verified=False, confidence=0.0, confidence_level="very_low",
            reason=f"Verification failed: {exc}", supporting_quote=None,
            source_url=claim.source_url, concerns=["LLM verification call failed"],
        )
    supporting_quote = j.supporting_quote or (claim.source_quote if _quote_in_text(claim.source_quote, source_text) else None)
    concerns = list(j.concerns)
    quote_present = _quote_in_text(supporting_quote, source_text)
    if j.verified and not quote_present:
        concerns.append("Supporting quote not found in scraped source text")
        confidence = min(j.confidence, 0.49)
        verified = False
    elif j.verified and quote_present:
        confidence = j.confidence
        verified = confidence >= 0.5
    else:
        # LLM said unverified — trust that, but still cap confidence if quote is missing
        confidence = j.confidence
        verified = False
    return VerificationResult(
        claim_id=claim.id, verified=verified, confidence=confidence,
        confidence_level=_confidence_level(confidence), reason=j.reason,
        supporting_quote=supporting_quote, source_url=claim.source_url, concerns=concerns,
    )


# ── Public API ────────────────────────────────────────────────────────────

async def verify_claims(
    request: VerificationRequest,
    model: str = "openai/gpt-4o",
    *,
    cancelled_check=None,
) -> VerificationOutput:
    """Verify claims against source text with multi-pass re-checking."""
    def _is_cancelled() -> bool:
        return cancelled_check() if cancelled_check else False

    if _is_cancelled():
        return VerificationOutput(results=[], total_claims=0, verified_count=0, flagged_count=0, passes_completed=0)

    claims = request.claims
    if not claims:
        return VerificationOutput(
            results=[], total_claims=0, verified_count=0, flagged_count=0, passes_completed=0
        )

    max_passes = request.verification_passes
    passes_completed = 1
    # Limit concurrent LLM calls to avoid rate limiting
    _sem = asyncio.Semaphore(5)

    async def _verify_with_limit(claim, source_text, model):
        async with _sem:
            return await _verify_single_claim(claim, source_text, model)

    tasks = [_verify_with_limit(c, _find_source_text(c, request.scrape_results), model) for c in claims]
    first_pass = await asyncio.gather(*tasks, return_exceptions=True)
    results: dict[str, VerificationResult] = {}
    for i, vr in enumerate(first_pass):
        if isinstance(vr, Exception):
            logger.warning("Verification failed for claim %s: %s", claims[i].id, vr)
            results[claims[i].id] = VerificationResult(
                claim_id=claims[i].id, verified=False, confidence=0.0,
                confidence_level="very_low", reason=f"Verification error: {vr}",
                source_url=claims[i].source_url, concerns=[str(vr)],
            )
        else:
            results[vr.claim_id] = vr

    # Additional passes: re-check anything unresolved or low-confidence.
    for pass_num in range(2, max_passes + 1):
        if _is_cancelled(): break
        flagged = [vr for vr in results.values() if (not vr.verified) or vr.confidence < 0.6]
        if not flagged: break
        logger.info("Verification pass %d: re-checking %d flagged claims", pass_num, len(flagged))
        passes_completed = pass_num

        claim_map = {c.id: c for c in claims}
        recheck_tasks = [_verify_with_limit(claim_map[vr.claim_id], _find_source_text(claim_map[vr.claim_id], request.scrape_results), model)
                         for vr in flagged if vr.claim_id in claim_map]
        if recheck_tasks:
            recheck_results = await asyncio.gather(*recheck_tasks, return_exceptions=True)
            for vr in recheck_results:
                if isinstance(vr, Exception):
                    logger.warning("Recheck verification failed: %s", vr)
                    continue
                results[vr.claim_id] = vr

    all_results = list(results.values())
    verified_count = sum(1 for r in all_results if r.verified)
    logger.info("Verification complete: %d total, %d verified, %d flagged", len(all_results), verified_count, len(all_results) - verified_count)

    return VerificationOutput(
        results=all_results, total_claims=len(all_results),
        verified_count=verified_count, flagged_count=len(all_results) - verified_count,
        passes_completed=passes_completed,
    )
