"""Mimo/OpenAI-compatible provider — raw httpx, no SDK overhead."""

from __future__ import annotations

import asyncio
import json
import os
import logging
from typing import TypeVar

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1").strip().rstrip("/")

async def extract_structured(
    prompt: str,
    response_model: type[T],
    *,
    model: str,
    system_prompt: str | None = None,
    max_retries: int = 3,
    temperature: float = 0.0,
    timeout: float = 60.0,
) -> T:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")
    schema = response_model.model_json_schema()
    sys_msg = f"""Parse the content and return a JSON object matching this schema:

{json.dumps(schema, indent=2)}

        Return a valid JSON instance, not the schema definition."""

    if system_prompt:
        sys_msg = f"{system_prompt}\n\n{sys_msg}"

    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "response_format": {"type": "json_object"},
        "stream": False,
    }

    url = f"{_API_BASE}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept-Encoding": "identity",
    }

    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=10.0)) as client:
                resp = await client.post(url, json=body, headers=headers)
                resp.raise_for_status()
                data = resp.json()

            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            return response_model.model_validate(parsed)

        except Exception as exc:
            last_exc = exc
            exc_str = str(exc).lower()
            is_retryable = any(k in exc_str for k in ("connection", "timeout", "502", "503", "504", "validation", "json"))
            if not is_retryable or attempt == max_retries - 1:
                raise
            delay = 2.0 * (2 ** attempt)
            logger.info("Retryable error (attempt %d/%d), waiting %.1fs: %s",
                        attempt + 1, max_retries, delay, exc)
            await asyncio.sleep(delay)

    raise last_exc or RuntimeError("mimo extract_structured failed")
