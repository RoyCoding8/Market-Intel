"""Engine pipeline stub — replaced by engine.pipeline.run_pipeline when available."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Optional

from contracts.engine import PipelineContext, ReportOutput

logger = logging.getLogger(__name__)

async def run_pipeline_stub(
    ctx: PipelineContext,
    emitter: Any,
    *,
    cancelled_check: Optional[Callable[[], bool]] = None,
) -> ReportOutput:
    """Placeholder that mimics a short pipeline run.

    The real implementation lives at ``engine.pipeline.run_pipeline``
    and will be swapped in once the engine agent finishes building it.
    """
    logger.info("[stub] Pipeline started for job %s", ctx.job_id)
    await asyncio.sleep(0.5)
    logger.info("[stub] Pipeline finished for job %s", ctx.job_id)
    return ReportOutput(
        executive_summary="[Stub] Pipeline completed with placeholder results. "
        "Install the engine package for real analysis.",
        findings=[],
        comparison_tables=[],
        recommendations=["Install the engine package for real competitive analysis"],
    )
