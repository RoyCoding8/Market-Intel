"""SSE event pub/sub store with per-job async queues."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import AsyncIterator, Optional

from contracts.events import AgentEvent, EventType
from engine.emitter import EventEmitter

logger = logging.getLogger(__name__)

# Max events to buffer per job for replay on reconnect
MAX_EVENTS_PER_JOB = 500


class EventStore(EventEmitter):
    """In-memory pub/sub event store.

    Each job gets its own set of subscriber queues and an event history
    for replay. The engine publishes events via ``publish``; the SSE
    endpoint subscribes via ``subscribe``.
    """

    def __init__(self) -> None:
        # job_id -> list of subscriber queues
        self._subscribers: dict[str, list[asyncio.Queue[AgentEvent | None]]] = defaultdict(list)
        # job_id -> ordered list of past events (capped)
        self._history: dict[str, list[AgentEvent]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def emit(self, event: AgentEvent) -> None:
        """Emit an event (EventEmitter interface). Delegates to publish."""
        await self.publish(event)

    async def publish(self, event: AgentEvent) -> None:
        """Publish an event to all subscribers of the given job."""
        async with self._lock:
            self._history[event.job_id].append(event)
            # Cap history length
            if len(self._history[event.job_id]) > MAX_EVENTS_PER_JOB:
                self._history[event.job_id] = self._history[event.job_id][-MAX_EVENTS_PER_JOB:]

            queues = self._subscribers.get(event.job_id, [])
            for q in queues:
                try:
                    q.put_nowait(event)
                except asyncio.QueueFull:
                    logger.warning("Event queue full for job %s, dropping event", event.job_id)

    async def subscribe(
        self,
        job_id: str,
        last_event_id: Optional[str] = None,
    ) -> AsyncIterator[AgentEvent]:
        """Yield events for *job_id*. Replays missed events when
        ``last_event_id`` is provided, then streams live events.

        The iterator ends when ``None`` is published (sentinel) or
        the job history shows a terminal event.
        """
        queue: asyncio.Queue[AgentEvent | None] = asyncio.Queue(maxsize=256)

        # Collect replay events while holding lock, then yield outside lock
        # to avoid blocking publish() during history replay.
        replay_events: list[AgentEvent] = []
        job_already_ended = False

        async with self._lock:
            history = self._history.get(job_id, [])
            replay_from = 0
            if last_event_id:
                for idx, ev in enumerate(history):
                    if ev.event_id == last_event_id:
                        replay_from = idx + 1
                        break

            replay_events = list(history[replay_from:])

            if history and history[-1].event_type in (
                EventType.JOB_COMPLETED,
                EventType.JOB_FAILED,
                EventType.JOB_CANCELLED,
            ):
                job_already_ended = True
            else:
                self._subscribers[job_id].append(queue)

        # Yield replayed events WITHOUT holding the lock
        for ev in replay_events:
            yield ev

        if job_already_ended:
            return

        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield event
        finally:
            async with self._lock:
                if queue in self._subscribers[job_id]:
                    self._subscribers[job_id].remove(queue)

    async def close_job(self, job_id: str) -> None:
        """Send sentinel to all subscribers and clean up."""
        async with self._lock:
            for q in self._subscribers.get(job_id, []):
                try:
                    q.put_nowait(None)
                except asyncio.QueueFull:
                    try:
                        q.get_nowait()
                        q.put_nowait(None)
                    except (asyncio.QueueEmpty, asyncio.QueueFull):
                        pass
            self._subscribers.pop(job_id, None)

    def get_history(self, job_id: str) -> list[AgentEvent]:
        """Return stored events for *job_id*."""
        return list(self._history.get(job_id, []))

    async def publish_heartbeat(self, job_id: str) -> None:
        """Publish a heartbeat event."""
        event = AgentEvent(
            event_id=f"heartbeat-{job_id}-{datetime.now(timezone.utc).timestamp()}",
            event_type=EventType.HEARTBEAT,
            job_id=job_id,
            agent_name="backend",
            timestamp=datetime.now(timezone.utc),
            message="heartbeat",
        )
        await self.publish(event)
