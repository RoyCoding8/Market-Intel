"""LLM wrapper — litellm + instructor with retry logic."""

from __future__ import annotations

import os
import logging
from typing import TypeVar

import instructor
from litellm import acompletion
from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# Singleton instructor client wrapping litellm
_client = instructor.from_litellm(acompletion)


def _default_model() -> str:
    """Return the configured LLM model, falling back to Xiaomi MiMo."""
    return os.getenv("LLM_MODEL", "openai/mimo-v2.5-pro")


async def extract_structured(
    prompt: str,
    response_model: type[T],
    *,
    model: str | None = None,
    system_prompt: str | None = None,
    max_retries: int = 3,
    temperature: float = 0.0,
    timeout: float = 60.0,
    **kwargs,
) -> T:
    """Call an LLM and parse the response into a structured Pydantic model.

    Uses instructor to enforce structured output with automatic retries
    on validation failures.

    Args:
        prompt: The user message sent to the LLM.
        response_model: Pydantic model class that defines the expected output.
        model: Override the default model (reads LLM_MODEL env var).
        system_prompt: Optional system message prepended to the conversation.
        max_retries: Number of retries on validation/parse failures.
        temperature: Sampling temperature (0.0 = deterministic).
        timeout: Per-call timeout in seconds (default 60).
        **kwargs: Additional keyword arguments forwarded to acompletion.

    Returns:
        An instance of *response_model* populated by the LLM.
    """
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    resolved_model = model or _default_model()

    logger.debug(
        "extract_structured model=%s retries=%d response_model=%s",
        resolved_model,
        max_retries,
        response_model.__name__,
    )

    result = await _client.chat.completions.create(
        model=resolved_model,
        response_model=response_model,
        messages=messages,
        max_retries=max_retries,
        temperature=temperature,
        timeout=timeout,
        **kwargs,
    )

    return result
