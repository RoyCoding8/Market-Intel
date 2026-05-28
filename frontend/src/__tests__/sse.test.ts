import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { connectJobStream } from '@/lib/sse';

// Mock EventSource
class MockEventSource {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSED = 2;
  static instances: MockEventSource[] = [];
  url: string;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  listeners: Map<string, Set<(e: MessageEvent) => void>> = new Map();
  closed = false;
  readyState = 1; // OPEN by default

  constructor(url: string) {
    this.url = url;
    MockEventSource.instances.push(this);
  }

  addEventListener(type: string, listener: (e: MessageEvent) => void) {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, new Set());
    }
    this.listeners.get(type)!.add(listener);
  }

  removeEventListener(type: string, listener: (e: MessageEvent) => void) {
    this.listeners.get(type)?.delete(listener);
  }

  close() {
    this.closed = true;
    this.readyState = 2; // CLOSED
  }

  // Test helper: simulate an event
  simulateEvent(eventType: string, data: string) {
    const listeners = this.listeners.get(eventType);
    const msgEvent = new MessageEvent(eventType, { data });
    if (listeners) {
      listeners.forEach((fn) => fn(msgEvent));
    }
  }

  // Test helper: simulate unnamed message
  simulateMessage(data: string) {
    const msgEvent = new MessageEvent('message', { data });
    this.onmessage?.(msgEvent);
  }

  // Test helper: simulate error
  simulateError() {
    this.onerror?.(new Event('error'));
  }
}

vi.stubGlobal('EventSource', MockEventSource);

describe('connectJobStream', () => {
  beforeEach(() => {
    MockEventSource.instances = [];
  });

  it('should create an EventSource with the correct URL', () => {
    connectJobStream('job-123', vi.fn());

    expect(MockEventSource.instances).toHaveLength(1);
    expect(MockEventSource.instances[0].url).toBe('http://localhost:8000/api/jobs/job-123/stream');
  });

  it('should call onEvent for named events', () => {
    const onEvent = vi.fn();
    connectJobStream('job-123', onEvent);

    const es = MockEventSource.instances[0];
    const eventData = JSON.stringify({
      event_id: 'evt-1',
      event_type: 'job.started',
      job_id: 'job-123',
      agent_name: 'orchestrator',
      timestamp: new Date().toISOString(),
      message: 'Job started',
    });

    es.simulateEvent('job.started', eventData);

    expect(onEvent).toHaveBeenCalledTimes(1);
    expect(onEvent).toHaveBeenCalledWith(expect.objectContaining({
      event_id: 'evt-1',
      event_type: 'job.started',
      message: 'Job started',
    }));
  });

  it('should call onEvent for unnamed onmessage events', () => {
    const onEvent = vi.fn();
    connectJobStream('job-123', onEvent);

    const es = MockEventSource.instances[0];
    const eventData = JSON.stringify({
      event_id: 'evt-2',
      event_type: 'step.started',
      job_id: 'job-123',
      agent_name: 'scraper',
      timestamp: new Date().toISOString(),
      message: 'Scraping started',
    });

    es.simulateMessage(eventData);

    expect(onEvent).toHaveBeenCalledTimes(1);
    expect(onEvent).toHaveBeenCalledWith(expect.objectContaining({
      event_type: 'step.started',
    }));
  });

  it('should silently skip heartbeat events', () => {
    const onEvent = vi.fn();
    connectJobStream('job-123', onEvent);

    const es = MockEventSource.instances[0];
    const heartbeatData = JSON.stringify({
      event_id: 'hb-1',
      event_type: 'heartbeat',
      job_id: 'job-123',
      agent_name: 'backend',
      timestamp: new Date().toISOString(),
      message: 'heartbeat',
    });

    es.simulateEvent('heartbeat', heartbeatData);

    expect(onEvent).not.toHaveBeenCalled();
  });

  it('should handle malformed JSON gracefully', () => {
    const onEvent = vi.fn();
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    connectJobStream('job-123', onEvent);

    const es = MockEventSource.instances[0];
    es.simulateMessage('not valid json{{{');

    expect(onEvent).not.toHaveBeenCalled();
    expect(consoleSpy).toHaveBeenCalled();
    consoleSpy.mockRestore();
  });

  it('should NOT call onError on transient error (readyState OPEN)', () => {
    const onError = vi.fn();
    connectJobStream('job-123', vi.fn(), onError);

    const es = MockEventSource.instances[0];
    es.readyState = 1; // OPEN — transient
    es.simulateError();

    expect(onError).not.toHaveBeenCalled();
    expect(es.closed).toBe(false);
  });

  it('should call onError and onClose on permanent close (readyState CLOSED)', () => {
    const onError = vi.fn();
    const onClose = vi.fn();
    connectJobStream('job-123', vi.fn(), onError, onClose);

    const es = MockEventSource.instances[0];
    es.readyState = 2; // CLOSED — permanent
    es.simulateError();

    expect(onError).toHaveBeenCalledTimes(1);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('should not call onError after close()', () => {
    const onError = vi.fn();
    const conn = connectJobStream('job-123', vi.fn(), onError);

    const es = MockEventSource.instances[0];
    conn.close();
    es.simulateError();

    expect(onError).not.toHaveBeenCalled();
  });

  it('should close the EventSource when close() is called', () => {
    const onClose = vi.fn();
    const conn = connectJobStream('job-123', vi.fn(), undefined, onClose);

    const es = MockEventSource.instances[0];
    conn.close();

    expect(es.closed).toBe(true);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('should not double-close', () => {
    const onClose = vi.fn();
    const conn = connectJobStream('job-123', vi.fn(), undefined, onClose);

    conn.close();
    conn.close();

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('should register listeners for all known event types', () => {
    connectJobStream('job-123', vi.fn());

    const es = MockEventSource.instances[0];
    const expectedTypes = [
      'job.started', 'job.completed', 'job.failed', 'job.cancelled',
      'step.started', 'step.completed', 'step.failed',
      'page.scraped', 'scraping.complete',
      'finding.found', 'comparison.generated',
      'claim.verified', 'claim.flagged', 'verification.complete',
      'report.generated', 'log', 'progress', 'heartbeat',
    ];

    for (const type of expectedTypes) {
      expect(es.listeners.has(type)).toBe(true);
    }
  });
});
