"""Tests for the event store pub/sub service."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from contracts.events import AgentEvent, EventType
from backend.services.event_store import EventStore


def _make_event(job_id: str, event_type: EventType = EventType.LOG, message: str = "test") -> AgentEvent:
    return AgentEvent(
        event_id=f"ev-{job_id}-{datetime.now(timezone.utc).timestamp()}",
        event_type=event_type,
        job_id=job_id,
        agent_name="test",
        timestamp=datetime.now(timezone.utc),
        message=message,
    )


@pytest.mark.asyncio
async def test_publish_and_subscribe(event_store: EventStore):
    job_id = "job-1"
    event = _make_event(job_id)

    # Start subscriber in background
    async def consume():
        collected = []
        async for ev in event_store.subscribe(job_id):
            collected.append(ev)
            if len(collected) >= 1:
                break
        return collected

    task = asyncio.create_task(consume())
    await asyncio.sleep(0.05)  # let subscriber attach
    await event_store.publish(event)
    collected = await asyncio.wait_for(task, timeout=2.0)
    assert len(collected) == 1
    assert collected[0].event_id == event.event_id


@pytest.mark.asyncio
async def test_replay_history(event_store: EventStore):
    job_id = "job-replay"
    events = [_make_event(job_id, message=f"msg-{i}") for i in range(5)]
    for ev in events:
        await event_store.publish(ev)
    # Publish terminal event so subscribe ends after replay
    await event_store.publish(_make_event(job_id, EventType.JOB_COMPLETED, "done"))

    # Subscribe with no last_event_id — should replay all 6 then stop
    collected = []
    async for ev in event_store.subscribe(job_id):
        collected.append(ev)
    assert len(collected) == 6  # 5 events + terminal


@pytest.mark.asyncio
async def test_replay_from_last_event_id(event_store: EventStore):
    job_id = "job-replay2"
    events = [_make_event(job_id, message=f"msg-{i}") for i in range(5)]
    for ev in events:
        await event_store.publish(ev)
    # Add terminal event so replay finishes cleanly
    await event_store.publish(_make_event(job_id, EventType.JOB_COMPLETED, "done"))

    # Replay starting from event #2 (index 2) — yields events 3, 4, and terminal
    last_id = events[2].event_id
    collected = []
    async for ev in event_store.subscribe(job_id, last_event_id=last_id):
        collected.append(ev)
    assert len(collected) == 3  # events[3], events[4], terminal
    assert collected[0].event_id == events[3].event_id
    assert collected[-1].event_type == EventType.JOB_COMPLETED


@pytest.mark.asyncio
async def test_close_job_sends_sentinel(event_store: EventStore):
    job_id = "job-close"

    async def consume():
        collected = []
        async for ev in event_store.subscribe(job_id):
            collected.append(ev)
        return collected

    task = asyncio.create_task(consume())
    await asyncio.sleep(0.05)
    await event_store.close_job(job_id)
    collected = await asyncio.wait_for(task, timeout=2.0)
    # Subscriber should have ended (empty because no events published)
    assert collected == []


@pytest.mark.asyncio
async def test_close_job_preserves_queued_terminal_event(event_store: EventStore):
    job_id = "job-close-terminal"
    terminal = _make_event(job_id, EventType.JOB_COMPLETED, "done")

    async def consume():
        collected = []
        async for ev in event_store.subscribe(job_id):
            collected.append(ev)
        return collected

    task = asyncio.create_task(consume())
    await asyncio.sleep(0.05)
    await event_store.publish(terminal)
    await event_store.close_job(job_id)

    collected = await asyncio.wait_for(task, timeout=2.0)
    assert collected[-1].event_id == terminal.event_id
    assert event_store.get_history(job_id)[-1].event_id == terminal.event_id


@pytest.mark.asyncio
async def test_publish_heartbeat(event_store: EventStore):
    job_id = "job-hb"

    async def consume():
        collected = []
        async for ev in event_store.subscribe(job_id):
            collected.append(ev)
            if len(collected) >= 1:
                break
        return collected

    task = asyncio.create_task(consume())
    await asyncio.sleep(0.05)
    await event_store.publish_heartbeat(job_id)
    collected = await asyncio.wait_for(task, timeout=2.0)
    assert len(collected) == 1
    assert collected[0].event_type == EventType.HEARTBEAT


@pytest.mark.asyncio
async def test_terminal_event_stops_replay(event_store: EventStore):
    job_id = "job-terminal"
    await event_store.publish(_make_event(job_id, EventType.JOB_STARTED, "started"))
    await event_store.publish(_make_event(job_id, EventType.JOB_COMPLETED, "done"))

    # New subscriber should get both events then stop
    collected = []
    async for ev in event_store.subscribe(job_id):
        collected.append(ev)
    assert len(collected) == 2
    assert collected[-1].event_type == EventType.JOB_COMPLETED
