"""Tests for the health check endpoint."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_ok(client: AsyncClient):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["version"] == "0.2.0"


@pytest.mark.asyncio
async def test_health_reports_scheduler(client: AsyncClient):
    resp = await client.get("/api/health")
    body = resp.json()
    # Scheduler may or may not be running depending on fixture timing;
    # the key thing is the field exists.
    assert "scheduler_running" in body
    assert "llm_configured" in body
