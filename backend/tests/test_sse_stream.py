"""Tests for the SSE streaming endpoint."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from contracts.api import CompetitorInput, CreateJobRequest
from contracts.events import AgentEvent, EventType

VALID_PAYLOAD = {
    "competitors": [{"url": "https://example.com", "name": "Ex"}],
}

@pytest.mark.asyncio
async def test_stream_404_for_unknown_job(client: AsyncClient):
    resp = await client.get("/api/jobs/nonexistent/stream")
    assert resp.status_code == 404

@pytest.mark.asyncio
async def test_stream_receives_events(client: AsyncClient, app):
    """Publish events manually to a pre-existing job record (no background
    pipeline) and verify the SSE stream delivers them."""
    event_store = app.state.event_store
    job_mgr = app.state.job_manager

    # Create a job record directly (bypass POST to avoid background task)
    job_id = "stream-test-job"
    request = CreateJobRequest(
        competitors=[CompetitorInput(url="https://example.com")],
    )
    await job_mgr.create_job(job_id, request)

    # Publish events, then terminal event
    for i in range(3):
        await event_store.publish(
            AgentEvent(
                event_id=f"test-{i}",
                event_type=EventType.LOG,
                job_id=job_id,
                agent_name="test",
                timestamp=datetime.now(timezone.utc),
                message=f"event-{i}",
            )
        )
    await event_store.publish(
        AgentEvent(
            event_id="test-done",
            event_type=EventType.JOB_COMPLETED,
            job_id=job_id,
            agent_name="test",
            timestamp=datetime.now(timezone.utc),
            message="done",
        )
    )

    # Open SSE stream — replay should deliver all 4 events then close
    collected_events = []
    async with client.stream("GET", f"/api/jobs/{job_id}/stream") as resp:
        assert resp.status_code == 200
        async for line in resp.aiter_lines():
            if line.startswith("data:"):
                data = json.loads(line[len("data:"):].strip())
                collected_events.append(data)

    assert len(collected_events) == 4
    assert collected_events[0]["message"] == "event-0"
    assert collected_events[-1]["event_type"] == "job.completed"
