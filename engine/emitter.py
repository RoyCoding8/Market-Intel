"""Abstract event emitter interface — engine emits, backend consumes."""

from __future__ import annotations

from abc import ABC, abstractmethod

from contracts.events import AgentEvent


class EventEmitter(ABC):
    """Abstract interface for emitting pipeline events.

    The backend provides a concrete implementation that writes events
    to the event store and forwards them as SSE to the frontend.
    The engine only depends on this abstract interface so it never
    imports backend code.
    """

    @abstractmethod
    async def emit(self, event: AgentEvent) -> None:
        """Emit a single AgentEvent.

        Implementations must be async-safe (may be called from many
        concurrent coroutines).  Errors should be logged but must not
        propagate — a failed emission must never crash the pipeline.
        """
        ...
