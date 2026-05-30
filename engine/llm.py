"""LLM wrapper — routes to mimo (httpx) or litellm (SDK) based on provider."""

from __future__ import annotations

import asyncio
import os
import logging
from typing import TypeVar

from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_LLM_RPM = int(os.getenv("LLM_RPM", "10"))
_DEFAULT_MODEL = os.getenv("LLM_MODEL", "openai/mimo-v2.5-pro")
_LITELLM_DEBUG = os.getenv("LITELLM_DEBUG", "").lower() in ("1", "true", "yes")

if _LITELLM_DEBUG:
    import litellm
    litellm._turn_on_debug()

def _default_model() -> str:
    return _DEFAULT_MODEL

def _is_mimo(model: str) -> bool:
    return model.startswith("openai/")

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
    resolved_model = model or _default_model()

    if _is_mimo(resolved_model):
        from engine.mimo import extract_structured as mimo_extract
        return await mimo_extract(
            prompt, response_model,
            model=resolved_model.replace("openai/", ""),
            system_prompt=system_prompt,
            max_retries=max_retries,
            temperature=temperature,
            timeout=timeout,
        )

    import instructor
    from litellm import acompletion

    client = instructor.from_litellm(acompletion, mode=instructor.Mode.JSON)

    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    logger.debug(
        "extract_structured model=%s retries=%d response_model=%s",
        resolved_model, max_retries, response_model.__name__,
    )

    result = await client.chat.completions.create(
        model=resolved_model,
        response_model=response_model,
        messages=messages,
        max_retries=max_retries,
        temperature=temperature,
        timeout=timeout,
        **kwargs,
    )

    return result

async def extract_with_retry(
    prompt: str,
    response_model: type[T],
    *,
    model: str | None = None,
    max_attempts: int = 3,
    base_delay: float = 2.0,
) -> T | None:
    for attempt in range(max_attempts):
        try:
            return await extract_structured(prompt, response_model, model=model)
        except Exception as exc:
            exc_str = str(exc).lower()
            is_retryable = any(k in exc_str for k in ("connection", "timeout", "502", "503", "504"))
            if not is_retryable or attempt == max_attempts - 1:
                logger.warning("LLM call failed (attempt %d/%d): %s", attempt + 1, max_attempts, exc)
                return None
            delay = base_delay * (2 ** attempt)
            logger.info("Retryable error (attempt %d/%d), waiting %.1fs: %s",
                        attempt + 1, max_attempts, delay, exc)
            await asyncio.sleep(delay)
    return None

async def run_sequential(
    calls: list[tuple[str, type[T]]],
    *,
    model: str | None = None,
    rpm: int | None = None,
    max_attempts: int = 3,
) -> list[T | None]:
    resolved_rpm = rpm or _LLM_RPM
    delay = 60.0 / resolved_rpm

    logger.info("run_sequential: %d calls, RPM=%d, delay=%.1fs", len(calls), resolved_rpm, delay)

    results = []
    for i, (prompt, response_model) in enumerate(calls):
        if i > 0:
            await asyncio.sleep(delay)

        result = await extract_with_retry(
            prompt, response_model, model=model, max_attempts=max_attempts,
        )
        results.append(result)

        if result is None:
            logger.warning("Call %d/%d failed", i + 1, len(calls))
        else:
            logger.debug("Call %d/%d complete", i + 1, len(calls))

    return results
