"""Pipeline orchestrator — runs scrape → analyze → verify → report (v2)."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Callable, Optional

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
    VerificationOutput,
    VerificationRequest,
)
from contracts.events import AgentEvent, EventType
from engine.agents.analyzer import analyze_competitor
from engine.agents.reporter import generate_report
from engine.agents.scraper import scrape_competitor
from engine.agents.verifier import verify_claims
from engine.emitter import EventEmitter

logger = logging.getLogger(__name__)


def _evt(ctx: PipelineContext, event_type: EventType, agent: str, message: str,
         data: dict | None = None) -> AgentEvent:
    """Create an AgentEvent with consistent metadata."""
    return AgentEvent(
        event_id=str(uuid.uuid4()), event_type=event_type, job_id=ctx.job_id,
        agent_name=agent, timestamp=datetime.now(timezone.utc),
        message=message, data=data,
    )


async def _emit(emitter: EventEmitter, ctx: PipelineContext,
                 event_type: EventType, agent: str, message: str,
                 data: dict | None = None) -> None:
    await emitter.emit(_evt(ctx, event_type, agent, message, data))


async def run_pipeline(
    ctx: PipelineContext,
    emitter: EventEmitter,
    *,
    cancelled_check: Optional[Callable[[], bool]] = None,
) -> ReportOutput:
    def _is_cancelled() -> bool:
        return cancelled_check() if cancelled_check else False

    # ── Job started ──────────────────────────────────────────────────────
    ctx.state = PipelineState.SCRAPING
    await _emit(emitter, ctx, EventType.JOB_STARTED, "pipeline", "Pipeline started")

    # ── Step 1: Scrape ───────────────────────────────────────────────────
    await _emit(emitter, ctx, EventType.STEP_STARTED, "pipeline", "Starting scraping")
    scrape_results: list[ScrapeResult] = []

    for url in ctx.competitor_urls:
        if _is_cancelled():
            logger.info("Pipeline cancelled before scraping %s", url)
            break
        try:
            request = ScrapeRequest(url=url, focus_areas=ctx.focus_areas, max_pages=ctx.max_pages_per_competitor)
            result = await scrape_competitor(request, cancelled_check=cancelled_check)
            scrape_results.append(result)

            for page in result.pages:
                await _emit(emitter, ctx, EventType.PAGE_SCRAPED, "scraper",
                            f"Scraped {page.url}", {
                                "url": page.url, "page_type": page.page_type,
                                "title": page.title, "content_length": len(page.html_text),
                                "content_quality": page.content_quality,
                                "scrape_provider": page.metadata.get("scrape_provider", "direct_httpx"),
                                "bright_data_enabled": page.metadata.get("bright_data_enabled", "false"),
                                "bright_data_zone": page.metadata.get("bright_data_zone"),
                                "anti_bot_detected": page.anti_bot_detected,
                            })

            bright_data_pages = sum(
                1
                for page in result.pages
                if page.metadata.get("bright_data_enabled") == "true"
            )
            scrape_provider = result.metadata.get("scrape_provider", "direct_httpx")
            await _emit(emitter, ctx, EventType.SCRAPING_COMPLETE, "scraper",
                        f"Scraped {len(result.pages)} pages from {url}", {
                            "competitor_url": url, "pages_scraped": len(result.pages),
                            "errors": len(result.errors), "robots_respected": result.robots_respected,
                            "bright_data_pages": bright_data_pages,
                            "scrape_provider": scrape_provider,
                            "bright_data_enabled": result.metadata.get("bright_data_enabled", "false"),
                            "bright_data_zone": result.metadata.get("bright_data_zone"),
                        })
        except Exception as exc:
            logger.error("Scraping failed for %s: %s", url, exc, exc_info=True)
            await _emit(emitter, ctx, EventType.STEP_FAILED, "scraper", f"Scraping failed for {url}: {type(exc).__name__}")

    if not scrape_results or all(not sr.pages for sr in scrape_results):
        if _is_cancelled():
            return await _partial_report(ctx, emitter, scrape_results, "Cancelled before scraping")
        ctx.state = PipelineState.ERROR
        await _emit(emitter, ctx, EventType.JOB_FAILED, "pipeline", "No pages were scraped")
        return ReportOutput(
            executive_summary="Pipeline failed: no pages could be scraped.",
            recommendations=["Check competitor URLs and try again"], findings=[], comparison_tables=[],
        )

    await _emit(emitter, ctx, EventType.STEP_COMPLETED, "pipeline", "Completed scraping")

    # ── Step 2: Analyze ──────────────────────────────────────────────────
    if _is_cancelled():
        return await _partial_report(ctx, emitter, scrape_results, "Cancelled before analysis")

    ctx.state = PipelineState.ANALYZING
    await _emit(emitter, ctx, EventType.STEP_STARTED, "pipeline", "Starting analyzing")
    analysis_results: list[AnalysisResult] = []

    for scrape in scrape_results:
        if _is_cancelled():
            logger.info("Pipeline cancelled during analysis")
            break
        try:
            analysis = await analyze_competitor(
                AnalysisRequest(scrape_result=scrape, query=ctx.query, focus_areas=ctx.focus_areas),
                model=ctx.llm_model,
            )
            analysis_results.append(analysis)

            for claim in analysis.claims:
                await _emit(emitter, ctx, EventType.FINDING_FOUND, "analyzer",
                            f"Found: {claim.text[:100]}", {
                                "finding_id": claim.id, "category": claim.category,
                                "source_url": claim.source_url,
                            })

            logger.info("Analyzed %s: %d claims", analysis.competitor_name, len(analysis.claims))
        except Exception as exc:
            logger.error("Analysis failed for %s: %s", scrape.competitor_url, exc, exc_info=True)
            await _emit(emitter, ctx, EventType.STEP_FAILED, "analyzer",
                        f"Analysis failed for {scrape.competitor_url}: {type(exc).__name__}")

    if not analysis_results:
        if _is_cancelled():
            return await _partial_report(ctx, emitter, scrape_results, "Cancelled during analysis")
        ctx.state = PipelineState.ERROR
        await _emit(emitter, ctx, EventType.JOB_FAILED, "pipeline", "Analysis produced no results")
        return ReportOutput(
            executive_summary="Pipeline failed: analysis produced no results.",
            recommendations=["Retry with different competitor URLs"], findings=[], comparison_tables=[],
        )

    await _emit(emitter, ctx, EventType.STEP_COMPLETED, "pipeline", "Completed analyzing")

    # ── Step 3: Verify ───────────────────────────────────────────────────
    if _is_cancelled():
        return await _partial_report(ctx, emitter, scrape_results, "Cancelled before verification",
                                     analysis_results=analysis_results)

    ctx.state = PipelineState.VERIFYING
    await _emit(emitter, ctx, EventType.STEP_STARTED, "pipeline", "Starting verifying")

    all_claims: list[Claim] = []
    for ar in analysis_results:
        all_claims.extend(ar.claims)

    try:
        verification = await verify_claims(
            VerificationRequest(
                claims=all_claims,
                scrape_results=scrape_results,
                verification_passes=ctx.verification_passes,
            ),
            model=ctx.llm_model, cancelled_check=cancelled_check,
        )

        for vr in verification.results:
            et = EventType.CLAIM_VERIFIED if vr.verified else EventType.CLAIM_FLAGGED
            await _emit(emitter, ctx, et, "verifier",
                        f"{'Verified' if vr.verified else 'Flagged'} claim {vr.claim_id}", {
                            "finding_id": vr.claim_id, "verified": vr.verified,
                            "confidence": vr.confidence_level, "reason": vr.reason,
                        })

        await _emit(emitter, ctx, EventType.VERIFICATION_COMPLETE, "verifier",
                    f"Verification complete: {verification.verified_count}/{verification.total_claims} verified", {
                        "total_claims": verification.total_claims,
                        "verified_count": verification.verified_count,
                        "flagged_count": verification.flagged_count,
                    })
    except Exception as exc:
        logger.error("Verification failed: %s", exc, exc_info=True)
        await _emit(emitter, ctx, EventType.STEP_FAILED, "verifier", f"Verification failed: {exc}")
        verification = VerificationOutput(
            results=[], total_claims=len(all_claims), verified_count=0,
            flagged_count=len(all_claims), passes_completed=0,
        )

    await _emit(emitter, ctx, EventType.STEP_COMPLETED, "pipeline", "Completed verifying")

    # ── Step 4: Report ───────────────────────────────────────────────────
    if _is_cancelled():
        return await _partial_report(ctx, emitter, scrape_results, "Cancelled before report generation",
                                     analysis_results=analysis_results, verification=verification)

    ctx.state = PipelineState.REPORTING
    await _emit(emitter, ctx, EventType.STEP_STARTED, "pipeline", "Starting reporting")

    try:
        report = await generate_report(
            ReportRequest(analysis_results=analysis_results, verification_output=verification, query=ctx.query),
            model=ctx.llm_model,
        )

        total_citations = sum(len(f.get("citations", [])) for f in report.findings)
        await _emit(emitter, ctx, EventType.REPORT_GENERATED, "reporter", "Report generated", {
            "findings_count": len(report.findings), "total_citations": total_citations,
            "verification_passes": verification.passes_completed,
        })
    except Exception as exc:
        logger.error("Report generation failed: %s", exc, exc_info=True)
        await _emit(emitter, ctx, EventType.STEP_FAILED, "reporter", f"Report generation failed: {exc}")
        report = ReportOutput(
            executive_summary="Report generation failed.",
            recommendations=["Retry report generation"], findings=[], comparison_tables=[],
        )
        ctx.state = PipelineState.ERROR
        await _emit(emitter, ctx, EventType.JOB_FAILED, "pipeline", f"Report generation failed: {exc}")
        return report

    await _emit(emitter, ctx, EventType.STEP_COMPLETED, "pipeline", "Completed reporting")

    # ── Done ─────────────────────────────────────────────────────────────
    ctx.state = PipelineState.DONE
    await _emit(emitter, ctx, EventType.JOB_COMPLETED, "pipeline", "Pipeline completed")
    return report


async def _partial_report(
    ctx: PipelineContext,
    emitter: EventEmitter,
    scrape_results: list[ScrapeResult],
    reason: str,
    analysis_results: Optional[list[AnalysisResult]] = None,
    verification: Optional[VerificationOutput] = None,
) -> ReportOutput:
    """Build a partial report when the pipeline is cancelled mid-flight."""
    ctx.state = PipelineState.DONE
    total_pages = sum(len(sr.pages) for sr in scrape_results)
    ars = analysis_results or []
    total_claims = sum(len(ar.claims) for ar in ars)
    unique_sources = len({c.source_url for ar in ars for c in ar.claims})

    await _emit(emitter, ctx, EventType.JOB_CANCELLED, "pipeline", f"Pipeline cancelled: {reason}", {
        "pages_scraped": total_pages, "claims_extracted": total_claims, "partial": True,
    })

    return ReportOutput(
        executive_summary=(
            f"Pipeline was cancelled: {reason}. "
            f"Partial results: {total_pages} pages scraped, {total_claims} claims extracted."
        ),
        findings=[], comparison_tables=[],
        recommendations=["Re-run the pipeline to get complete results"],
        total_sources=unique_sources,
    )
