/**
 * SSE client helper for streaming agent events from the backend.
 * Connects directly to FastAPI SSE endpoint (not through Next.js).
 *
 * The backend sends named SSE events (event: job.started, etc.) via
 * sse-starlette's EventSourceResponse. The browser's EventSource API
 * only delivers named events to addEventListener() handlers, NOT to
 * onmessage. We register listeners for every known EventType so no
 * events are silently dropped.
 */

import type { AgentEvent, EventType } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** All event types the backend may emit. */
const ALL_EVENT_TYPES: EventType[] = [
  "job.started",
  "job.completed",
  "job.failed",
  "job.cancelled",
  "step.started",
  "step.completed",
  "step.failed",
  "page.scraped",
  "scraping.complete",
  "finding.found",
  "comparison.generated",
  "claim.verified",
  "claim.flagged",
  "verification.complete",
  "report.generated",
  "log",
  "progress",
  "heartbeat",
];

export type SSEEventHandler = (event: AgentEvent) => void;
export type SSEErrorHandler = (error: Event) => void;
export type SSECloseHandler = () => void;

export interface SSEConnection {
  close: () => void;
}

/**
 * Connect to the job event stream. Returns a connection object with a close() method.
 * Automatically parses JSON messages and dispatches typed AgentEvents.
 *
 * Handles both named SSE events (backend sends `event: <type>`) and unnamed
 * events (fallback via onmessage). Heartbeat events are silently consumed.
 */
export function connectJobStream(
  jobId: string,
  onEvent: SSEEventHandler,
  onError?: SSEErrorHandler,
  onClose?: SSECloseHandler
): SSEConnection {
  const url = `${API_BASE}/api/jobs/${jobId}/stream`;
  const es = new EventSource(url);

  let closed = false;

  function dispatch(e: MessageEvent) {
    try {
      const event: AgentEvent = JSON.parse(e.data);
      if (event.event_type === "heartbeat") return;
      onEvent(event);
    } catch (err) {
      console.error("[SSE] Failed to parse event:", e.data, err);
    }
  }

  for (const eventType of ALL_EVENT_TYPES) {
    es.addEventListener(eventType, dispatch as EventListener);
  }

  es.onmessage = dispatch;

  es.onerror = (e: Event) => {
    if (closed) return;
    if (es.readyState === EventSource.CLOSED) {
      console.warn("[SSE] Connection permanently closed for job", jobId);
      closed = true;
      if (onError) onError(e);
      if (onClose) onClose();
    } else {
      console.warn("[SSE] Transient error for job", jobId, "— will auto-reconnect");
    }
  };

  return {
    close: () => {
      if (closed) return;
      closed = true;
      es.close();
      if (onClose) onClose();
    },
  };
}
