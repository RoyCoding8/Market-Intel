"""Tests for the LLM wrapper."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from pydantic import BaseModel

from engine.llm import extract_structured


class _SimpleModel(BaseModel):
    name: str
    value: int


@pytest.mark.asyncio
async def test_extract_structured_calls_client():
    """extract_structured should call the instructor client and return the model."""
    expected = _SimpleModel(name="test", value=42)

    mock_create = AsyncMock(return_value=expected)

    with patch("engine.llm._client") as mock_client:
        mock_client.chat.completions.create = mock_create

        result = await extract_structured(
            "Test prompt",
            _SimpleModel,
            model="test-model",
        )

    assert result.name == "test"
    assert result.value == 42
    mock_create.assert_called_once()
    call_kwargs = mock_create.call_args
    assert call_kwargs.kwargs["model"] == "test-model"
    assert call_kwargs.kwargs["response_model"] is _SimpleModel


@pytest.mark.asyncio
async def test_extract_structured_uses_system_prompt():
    """System prompt should be prepended as a system message."""
    expected = _SimpleModel(name="x", value=1)
    mock_create = AsyncMock(return_value=expected)

    with patch("engine.llm._client") as mock_client:
        mock_client.chat.completions.create = mock_create

        await extract_structured(
            "User message",
            _SimpleModel,
            system_prompt="You are a test assistant.",
        )

    messages = mock_create.call_args.kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == "You are a test assistant."
    assert messages[1]["role"] == "user"


@pytest.mark.asyncio
async def test_extract_structured_passes_temperature():
    """Temperature should be forwarded to the client."""
    expected = _SimpleModel(name="x", value=1)
    mock_create = AsyncMock(return_value=expected)

    with patch("engine.llm._client") as mock_client:
        mock_client.chat.completions.create = mock_create

        await extract_structured("Test", _SimpleModel, temperature=0.5)

    assert mock_create.call_args.kwargs["temperature"] == 0.5


@pytest.mark.asyncio
async def test_extract_structured_passes_max_retries():
    """max_retries should be forwarded to the client."""
    expected = _SimpleModel(name="x", value=1)
    mock_create = AsyncMock(return_value=expected)

    with patch("engine.llm._client") as mock_client:
        mock_client.chat.completions.create = mock_create

        await extract_structured("Test", _SimpleModel, max_retries=5)

    assert mock_create.call_args.kwargs["max_retries"] == 5
