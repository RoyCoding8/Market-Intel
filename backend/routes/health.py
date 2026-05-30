"""Health check endpoint."""

from __future__ import annotations

import os

from fastapi import APIRouter, Request

from contracts.api import HealthResponse

router = APIRouter(tags=["health"])

_PROVIDER_KEY_VARS = [
    "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "AZURE_API_KEY",
    "DEEPSEEK_API_KEY", "MISTRAL_API_KEY", "COHERE_API_KEY", "GROQ_API_KEY",
    "TOGETHERAI_API_KEY", "FIREWORKS_API_KEY", "REPLICATE_API_TOKEN",
    "HUGGINGFACE_API_KEY", "AWS_ACCESS_KEY_ID", "XAI_API_KEY",
    "NVIDIA_NIM_API_KEY", "CEREBRAS_API_KEY", "SAMBANOVA_API_KEY",
    "DATABRICKS_API_KEY", "XIAOMI_MIMO_API_KEY",
]

def _llm_configured() -> bool:
    """Return True if an LLM model is configured and at least one provider key is set."""
    model = os.getenv("LLM_MODEL", "")
    if not model:
        return False
    # Ollama and local endpoints don't need an API key
    if model.startswith("ollama/"):
        return True
    # Any OpenAI-compatible endpoint with a base URL may not need a key
    if os.getenv("OPENAI_API_BASE") and os.getenv("OPENAI_API_KEY"):
        return True
    return any(os.getenv(var) for var in _PROVIDER_KEY_VARS)

def _bright_data_configured() -> bool:
    """Return True if all three Bright Data credentials are set."""
    return all(
        os.getenv(var, "").strip()
        for var in ("BRIGHT_DATA_CUSTOMER_ID", "BRIGHT_DATA_ZONE", "BRIGHT_DATA_PASSWORD")
    )

@router.get("/api/health", response_model=HealthResponse)
async def health_check(request: Request) -> HealthResponse:
    """Liveness / readiness probe.

    Returns scheduler state from the app-level scheduler service.
    """
    scheduler = request.app.state.scheduler
    job_mgr = request.app.state.job_manager
    records = await job_mgr.list_records()
    return HealthResponse(
        status="ok",
        version=request.app.version,
        llm_configured=_llm_configured(),
        bright_data_configured=_bright_data_configured(),
        scheduler_running=scheduler.running,
        active_jobs=sum(1 for r in records if r.status.value not in {"completed", "failed", "cancelled"}),
        total_jobs_completed=sum(1 for r in records if r.status.value == "completed"),
    )
