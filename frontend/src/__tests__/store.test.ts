import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { CreateJobResponse } from '@/types';
import { useJobStore } from '@/stores/jobStore';

// Mock API and SSE modules
vi.mock('@/lib/api', () => ({
  createJob: vi.fn(),
  getJobStatus: vi.fn(),
  getReport: vi.fn(),
  listJobs: vi.fn(),
  cancelJob: vi.fn(),
}));

vi.mock('@/lib/sse', () => ({
  connectJobStream: vi.fn(() => ({
    close: vi.fn(),
  })),
}));

vi.mock('@/components/ui/toast', () => ({
  toast: vi.fn(),
}));

import { createJob, getJobStatus, getReport, listJobs, cancelJob } from '@/lib/api';
import { connectJobStream } from '@/lib/sse';

const mockCreateJob = vi.mocked(createJob);
const mockGetJobStatus = vi.mocked(getJobStatus);
const mockGetReport = vi.mocked(getReport);
const mockListJobs = vi.mocked(listJobs);
const mockCancelJob = vi.mocked(cancelJob);
const mockConnectJobStream = vi.mocked(connectJobStream);

describe('jobStore', () => {
  beforeEach(() => {
    // Reset store to initial state
    useJobStore.setState({
      activeJobId: null,
      events: [],
      jobStatus: null,
      report: null,
      jobs: [],
      isLoading: false,
      error: null,
      isDemoMode: true,
      _sseConnection: null,
    });
    vi.clearAllMocks();
    mockGetJobStatus.mockRejectedValue(new Error('status unavailable'));
  });

  describe('initial state', () => {
    it('should have correct initial values', () => {
      const state = useJobStore.getState();
      expect(state.activeJobId).toBeNull();
      expect(state.events).toEqual([]);
      expect(state.jobStatus).toBeNull();
      expect(state.report).toBeNull();
      expect(state.jobs).toEqual([]);
      expect(state.isLoading).toBe(false);
      expect(state.error).toBeNull();
      expect(state.isDemoMode).toBe(true);
    });
  });

  describe('loadDemoData', () => {
    it('should populate state with demo data', () => {
      useJobStore.getState().loadDemoData();

      const state = useJobStore.getState();
      expect(state.activeJobId).toBe('demo-job-001');
      expect(state.events.length).toBeGreaterThan(0);
      expect(state.jobStatus).not.toBeNull();
      expect(state.report).not.toBeNull();
      expect(state.jobs.length).toBeGreaterThan(0);
      expect(state.isDemoMode).toBe(true);
      expect(state.isLoading).toBe(false);
      expect(state.error).toBeNull();
    });
  });

  describe('createJob', () => {
    it('should call API and update state on success', async () => {
      mockCreateJob.mockResolvedValue({
        job_id: 'new-job-123',
        status: 'pending',
        message: 'Job created',
      });

      const jobId = await useJobStore.getState().createJob({
        competitors: [{ url: 'https://example.com', focus_areas: ['pricing'] }],
      });

      expect(jobId).toBe('new-job-123');
      const state = useJobStore.getState();
      expect(state.activeJobId).toBe('new-job-123');
      expect(state.events).toEqual([]);
      expect(state.jobStatus).toMatchObject({
        job_id: 'new-job-123',
        status: 'pending',
        progress: 0,
      });
      expect(state.report).toBeNull();
      expect(state.isLoading).toBe(false);
      expect(state.error).toBeNull();
      expect(state.isDemoMode).toBe(false);
    });

    it('should connect SSE after creating job', async () => {
      mockCreateJob.mockResolvedValue({
        job_id: 'new-job-123',
        status: 'pending',
        message: 'Job created',
      });

      await useJobStore.getState().createJob({
        competitors: [{ url: 'https://example.com', focus_areas: ['pricing'] }],
      });

      expect(mockConnectJobStream).toHaveBeenCalledWith(
        'new-job-123',
        expect.any(Function),
        expect.any(Function),
        expect.any(Function)
      );
    });

    it('should set error on API failure', async () => {
      mockCreateJob.mockRejectedValue(new Error('Network error'));

      await expect(
        useJobStore.getState().createJob({
          competitors: [{ url: 'https://example.com', focus_areas: ['pricing'] }],
        })
      ).rejects.toThrow('Network error');

      const state = useJobStore.getState();
      expect(state.error).toBe('Network error');
      expect(state.isLoading).toBe(false);
    });

    it('should set loading state during creation', async () => {
      let resolveCreate: (v: CreateJobResponse) => void;
      mockCreateJob.mockImplementation(
        () => new Promise((resolve) => { resolveCreate = resolve as (v: CreateJobResponse) => void; })
      );

      const promise = useJobStore.getState().createJob({
        competitors: [{ url: 'https://example.com', focus_areas: ['pricing'] }],
      });

      expect(useJobStore.getState().isLoading).toBe(true);

      resolveCreate!({ job_id: 'x', status: 'pending', message: 'ok' });
      await promise;

      expect(useJobStore.getState().isLoading).toBe(false);
    });
  });

  describe('addEvent', () => {
    it('should append event to events array', () => {
      const event = {
        event_id: 'evt-1',
        event_type: 'job.started' as const,
        job_id: 'job-1',
        agent_name: 'orchestrator',
        timestamp: new Date().toISOString(),
        message: 'Job started',
      };

      useJobStore.getState().addEvent(event);

      expect(useJobStore.getState().events).toHaveLength(1);
      expect(useJobStore.getState().events[0]).toEqual(event);
    });

    it('should update job status on job.completed event', () => {
      useJobStore.setState({
        jobStatus: {
          job_id: 'job-1',
          status: 'scraping',
          progress: 0.5,
          competitors_found: 2,
          pages_scraped: 4,
          findings_count: 0,
        },
      });

      const event = {
        event_id: 'evt-complete',
        event_type: 'job.completed' as const,
        job_id: 'job-1',
        agent_name: 'orchestrator',
        timestamp: new Date().toISOString(),
        message: 'Job completed',
      };

      useJobStore.getState().addEvent(event);

      expect(useJobStore.getState().jobStatus!.status).toBe('completed');
      expect(useJobStore.getState().jobStatus!.progress).toBe(1.0);
    });

    it('should update job status on job.failed event', () => {
      useJobStore.setState({
        jobStatus: {
          job_id: 'job-1',
          status: 'scraping',
          progress: 0.5,
          competitors_found: 2,
          pages_scraped: 4,
          findings_count: 0,
        },
      });

      const event = {
        event_id: 'evt-fail',
        event_type: 'job.failed' as const,
        job_id: 'job-1',
        agent_name: 'orchestrator',
        timestamp: new Date().toISOString(),
        message: 'LLM timeout',
      };

      useJobStore.getState().addEvent(event);

      expect(useJobStore.getState().jobStatus!.status).toBe('failed');
      expect(useJobStore.getState().jobStatus!.error).toBe('LLM timeout');
    });

    it('should update job status on job.cancelled event', () => {
      useJobStore.setState({
        jobStatus: {
          job_id: 'job-1',
          status: 'scraping',
          progress: 0.5,
          competitors_found: 2,
          pages_scraped: 4,
          findings_count: 0,
        },
      });

      const event = {
        event_id: 'evt-cancel',
        event_type: 'job.cancelled' as const,
        job_id: 'job-1',
        agent_name: 'orchestrator',
        timestamp: new Date().toISOString(),
        message: 'Cancelled',
      };

      useJobStore.getState().addEvent(event);

      expect(useJobStore.getState().jobStatus!.status).toBe('cancelled');
    });

    it('should update progress from progress events', () => {
      useJobStore.setState({
        jobStatus: {
          job_id: 'job-1',
          status: 'scraping',
          progress: 0.0,
          competitors_found: 2,
          pages_scraped: 0,
          findings_count: 0,
        },
      });

      const event = {
        event_id: 'evt-prog',
        event_type: 'progress' as const,
        job_id: 'job-1',
        agent_name: 'scraper',
        timestamp: new Date().toISOString(),
        message: 'Progress update',
        data: { progress: 0.6, step: 'analyzing' },
      };

      useJobStore.getState().addEvent(event);

      expect(useJobStore.getState().jobStatus!.progress).toBe(0.6);
      expect(useJobStore.getState().jobStatus!.current_step).toBe('analyzing');
    });
  });

  describe('cancelActiveJob', () => {
    it('should call cancelJob API and update status', async () => {
      mockCancelJob.mockResolvedValue({
        job_id: 'job-1',
        status: 'cancelled',
        message: 'Job cancelled',
      });

      useJobStore.setState({
        activeJobId: 'job-1',
        jobStatus: {
          job_id: 'job-1',
          status: 'scraping',
          progress: 0.5,
          competitors_found: 2,
          pages_scraped: 4,
          findings_count: 0,
        },
      });

      await useJobStore.getState().cancelActiveJob();

      expect(mockCancelJob).toHaveBeenCalledWith('job-1');
      expect(useJobStore.getState().jobStatus!.status).toBe('cancelled');
    });

    it('should do nothing if no active job', async () => {
      useJobStore.setState({ activeJobId: null });

      await useJobStore.getState().cancelActiveJob();

      expect(mockCancelJob).not.toHaveBeenCalled();
    });
  });

  describe('fetchJobs', () => {
    it('should update jobs list from API', async () => {
      const jobs = [
        { job_id: 'j1', status: 'completed' as const, progress: 1, competitors_found: 2, pages_scraped: 10, findings_count: 5 },
        { job_id: 'j2', status: 'pending' as const, progress: 0, competitors_found: 1, pages_scraped: 0, findings_count: 0 },
      ];
      mockListJobs.mockResolvedValue({ jobs, total: 2 });

      await useJobStore.getState().fetchJobs();

      expect(useJobStore.getState().jobs).toEqual(jobs);
    });

    it('should silently fail if API is unavailable', async () => {
      mockListJobs.mockRejectedValue(new Error('Network error'));

      await useJobStore.getState().fetchJobs();

      // Should not throw, state unchanged
      expect(useJobStore.getState().jobs).toEqual([]);
    });
  });

  describe('fetchReport', () => {
    it('should update report from API', async () => {
      const report = {
        id: 'r1',
        title: 'Test Report',
        created_at: new Date().toISOString(),
        competitors: [],
        findings: [],
        comparison_tables: [],
        executive_summary: 'Summary',
        recommendations: [],
        total_sources: 5,
        verification_passes: 2,
      };
      mockGetReport.mockResolvedValue({ report });

      await useJobStore.getState().fetchReport('job-1');

      expect(useJobStore.getState().report).toEqual(report);
    });

    it('should silently fail if report not ready', async () => {
      mockGetReport.mockRejectedValue(new Error('Not completed'));

      await useJobStore.getState().fetchReport('job-1');

      expect(useJobStore.getState().report).toBeNull();
    });
  });

  describe('clearActive', () => {
    it('should reset active state', () => {
      useJobStore.setState({
        activeJobId: 'job-1',
        events: [{ event_id: 'e1', event_type: 'job.started', job_id: 'job-1', agent_name: 'orchestrator', timestamp: '', message: '' }],
        jobStatus: { job_id: 'job-1', status: 'scraping', progress: 0.5, competitors_found: 2, pages_scraped: 4, findings_count: 0 },
        report: { id: 'r1', title: 'R', created_at: '', competitors: [], findings: [], comparison_tables: [], executive_summary: '', recommendations: [], total_sources: 0, verification_passes: 0 },
        error: 'some error',
      });

      useJobStore.getState().clearActive();

      const state = useJobStore.getState();
      expect(state.activeJobId).toBeNull();
      expect(state.events).toEqual([]);
      expect(state.jobStatus).toBeNull();
      expect(state.report).toBeNull();
      expect(state.error).toBeNull();
    });
  });

  describe('setJobStatus', () => {
    it('should set job status directly', () => {
      const status = {
        job_id: 'j1',
        status: 'analyzing' as const,
        progress: 0.7,
        competitors_found: 3,
        pages_scraped: 15,
        findings_count: 4,
      };

      useJobStore.getState().setJobStatus(status);

      expect(useJobStore.getState().jobStatus).toEqual(status);
    });
  });

  describe('setReport', () => {
    it('should set report directly', () => {
      const report = {
        id: 'r1',
        title: 'Test',
        created_at: '',
        competitors: [],
        findings: [],
        comparison_tables: [],
        executive_summary: '',
        recommendations: [],
        total_sources: 0,
        verification_passes: 0,
      };

      useJobStore.getState().setReport(report);

      expect(useJobStore.getState().report).toEqual(report);
    });
  });

  describe('setError', () => {
    it('should set error', () => {
      useJobStore.getState().setError('test error');
      expect(useJobStore.getState().error).toBe('test error');
    });

    it('should clear error with null', () => {
      useJobStore.setState({ error: 'existing' });
      useJobStore.getState().setError(null);
      expect(useJobStore.getState().error).toBeNull();
    });
  });

  describe('setActiveJob', () => {
    it('should set active job and clear previous state', () => {
      useJobStore.setState({
        activeJobId: 'old-job',
        events: [{ event_id: 'e1', event_type: 'job.started', job_id: 'old-job', agent_name: '', timestamp: '', message: '' }],
        report: { id: 'r1', title: '', created_at: '', competitors: [], findings: [], comparison_tables: [], executive_summary: '', recommendations: [], total_sources: 0, verification_passes: 0 },
        isDemoMode: true,
      });

      useJobStore.getState().setActiveJob('new-job');

      const state = useJobStore.getState();
      expect(state.activeJobId).toBe('new-job');
      expect(state.events).toEqual([]);
      expect(state.report).toBeNull();
      expect(state.isDemoMode).toBe(false);
    });

    it('should fetch report and connect SSE for new job', () => {
      useJobStore.getState().setActiveJob('new-job');

      expect(mockGetReport).toHaveBeenCalledWith('new-job');
      expect(mockConnectJobStream).toHaveBeenCalledWith(
        'new-job',
        expect.any(Function),
        expect.any(Function),
        expect.any(Function)
      );
    });
  });
});
