"""Tests for the LLM wrapper."""

from __future__ import annotations

import os
os.environ.setdefault("OPENAI_API_KEY", "test-key")

from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from pydantic import BaseModel

from engine.llm import extract_structured

class _SimpleModel(BaseModel):
    name: str
    value: int

def _mock_httpx(response_json: dict):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = response_json
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)

    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_client)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    return mock_ctx

@pytest.mark.asyncio
async def test_extract_structured_calls_mimo():
    resp = {"choices": [{"message": {"content": '{"name": "test", "value": 42}'}}]}

    with patch("engine.mimo.httpx.AsyncClient", return_value=_mock_httpx(resp)):
        result = await extract_structured("Test prompt", _SimpleModel, model="openai/test-model")

    assert result.name == "test"
    assert result.value == 42

@pytest.mark.asyncio
async def test_extract_structured_uses_system_prompt():
    resp = {"choices": [{"message": {"content": '{"name": "x", "value": 1}'}}]}
    mock_ctx = _mock_httpx(resp)

    with patch("engine.mimo.httpx.AsyncClient", return_value=mock_ctx):
        await extract_structured(
            "User message", _SimpleModel,
            model="openai/test-model",
            system_prompt="You are a test assistant.",
        )

    client = await mock_ctx.__aenter__()
    call_body = client.post.call_args.kwargs.get("json", {})
    messages = call_body.get("messages", [])
    assert any("test assistant" in m.get("content", "").lower() for m in messages)

@pytest.mark.asyncio
async def test_extract_structured_passes_temperature():
    resp = {"choices": [{"message": {"content": '{"name": "x", "value": 1}'}}]}
    mock_ctx = _mock_httpx(resp)

    with patch("engine.mimo.httpx.AsyncClient", return_value=mock_ctx):
        await extract_structured("Test", _SimpleModel, model="openai/test-model", temperature=0.5)

    client = await mock_ctx.__aenter__()
    call_body = client.post.call_args.kwargs.get("json", {})
    assert call_body.get("temperature") == 0.5
