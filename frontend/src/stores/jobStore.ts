"use client";

import { create } from "zustand";
import type {
  AgentEvent,
  JobStatusResponse,
  IntelligenceReport,
  CreateJobRequest,
} from "@/types";
import { createJob as apiCreateJob, getJobStatus, getReport, listJobs, cancelJob } from "@/lib/api";
import { connectJobStream } from "@/lib/sse";
import { toast } from "@/components/ui/toast";
import { DEMO_EVENTS, DEMO_JOB_STATUS, DEMO_JOBS, DEMO_REPORT } from "@/lib/demoData";

interface JobStore {
  // ── State ──────────────────────────────────────────────────────────────
  activeJobId: string | null;
  events: AgentEvent[];
  jobStatus: JobStatusResponse | null;
  report: IntelligenceReport | null;
  jobs: JobStatusResponse[];
  isLoading: boolean;
  error: string | null;
  isDemoMode: boolean;

  // ── Actions ────────────────────────────────────────────────────────────
  createJob: (payload: CreateJobRequest) => Promise<string>;
  setActiveJob: (jobId: string) => void;
  loadDemoData: () => void;
  addEvent: (event: AgentEvent) => void;
  setJobStatus: (status: JobStatusResponse) => void;
  setReport: (report: IntelligenceReport) => void;
  setError: (error: string | null) => void;
  fetchJobs: () => Promise<void>;
  fetchReport: (jobId: string) => Promise<void>;
  cancelActiveJob: () => Promise<void>;
  clearActive: () => void;

  // SSE connection
  _sseConnection: ReturnType<typeof connectJobStream> | null;
  connectSSE: (jobId: string) => void;
  disconnectSSE: () => void;
}

export const useJobStore = create<JobStore>((set, get) => ({
  // ── Initial State ──────────────────────────────────────────────────────
  activeJobId: null,
  events: [],
  jobStatus: null,
  report: null,
  jobs: [],
  isLoading: false,
  error: null,
  isDemoMode: true,
  _sseConnection: null,

  // ── Actions ────────────────────────────────────────────────────────────

  loadDemoData: () => {
    set({
      activeJobId: "demo-job-001",
      events: DEMO_EVENTS,
      jobStatus: DEMO_JOB_STATUS,
      report: DEMO_REPORT,
      jobs: DEMO_JOBS,
      isDemoMode: true,
      isLoading: false,
      error: null,
    });
  },

  createJob: async (payload: CreateJobRequest) => {
    const wasDemo = get().isDemoMode;
    set({ isLoading: true, error: null, isDemoMode: false });

    // Clear old SSE if any
    get().disconnectSSE();

    try {
      const res = await apiCreateJob(payload);
      const jobId = res.job_id;

      set({
        activeJobId: jobId,
        events: [],
        jobStatus: {
          job_id: jobId,
          status: "pending",
          progress: 0,
          competitors_found: payload.competitors.length,
          pages_scraped: 0,
          findings_count: 0,
        },
        report: null,
        isLoading: false,
      });

      // Connect SSE for real-time events
      get().connectSSE(jobId);
      void get().fetchJobs();

      toast({
        variant: "success",
        title: "Job Created",
        description: `Analysis started with ${payload.competitors.length} competitor(s).`,
      });

      return jobId;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to create job";
      set({ error: message, isLoading: false, isDemoMode: wasDemo });
      toast({ variant: "error", title: "Job Creation Failed", description: message });
      throw err;
    }
  },

  setActiveJob: (jobId: string) => {
    get().disconnectSSE();
    set({
      activeJobId: jobId,
      events: [],
      report: null,
      jobStatus: {
        job_id: jobId,
        status: "pending",
        progress: 0,
        competitors_found: 0,
        pages_scraped: 0,
        findings_count: 0,
      },
      error: null,
      isDemoMode: false,
    });
    // Fetch latest status + connect SSE
    getJobStatus(jobId)
      .then((status) => set({ jobStatus: status }))
      .catch(() => {
        // Keep the console available even if the status endpoint is temporarily unavailable.
      });
    get().fetchReport(jobId);
    get().connectSSE(jobId);
  },

  addEvent: (event: AgentEvent) => {
    // Dedup by event_id — skip if already present
    if (get().events.some((e) => e.event_id && e.event_id === event.event_id)) return;
    set((state) => ({ events: [...state.events, event] }));

    // Auto-update job status from events
    const statusUpdate: Partial<JobStatusResponse> = {};
    if (event.event_type === "job.completed") {
      statusUpdate.status = "completed";
      statusUpdate.progress = 1.0;
      statusUpdate.completed_at = event.timestamp;
      toast({ variant: "success", title: "Job Completed", description: event.message });
    } else if (event.event_type === "job.failed") {
      statusUpdate.status = "failed";
      statusUpdate.error = event.message;
      toast({ variant: "error", title: "Job Failed", description: event.message });
    } else if (event.event_type === "job.cancelled") {
      statusUpdate.status = "cancelled";
      statusUpdate.error = "Cancelled by user";
      toast({ variant: "info", title: "Job Cancelled", description: "The job was cancelled." });
    } else if (event.event_type === "step.started") {
      const message = event.message.toLowerCase();
      if (message.includes("scraping")) {
        statusUpdate.status = "scraping";
        statusUpdate.progress = Math.max(get().jobStatus?.progress ?? 0, 0.1);
        statusUpdate.current_step = "scraping";
      } else if (message.includes("analyzing")) {
        statusUpdate.status = "analyzing";
        statusUpdate.progress = Math.max(get().jobStatus?.progress ?? 0, 0.35);
        statusUpdate.current_step = "analyzing";
      } else if (message.includes("verifying")) {
        statusUpdate.status = "verifying";
        statusUpdate.progress = Math.max(get().jobStatus?.progress ?? 0, 0.65);
        statusUpdate.current_step = "verifying";
      } else if (message.includes("reporting")) {
        statusUpdate.status = "generating_report";
        statusUpdate.progress = Math.max(get().jobStatus?.progress ?? 0, 0.85);
        statusUpdate.current_step = "generating_report";
      }
    } else if (event.event_type === "page.scraped") {
      const pages = get().events.filter((e) => e.event_type === "page.scraped").length;
      statusUpdate.pages_scraped = Math.max(get().jobStatus?.pages_scraped ?? 0, pages);
    } else if (event.event_type === "finding.found") {
      const findings = get().events.filter((e) => e.event_type === "finding.found").length;
      statusUpdate.findings_count = Math.max(get().jobStatus?.findings_count ?? 0, findings);
    } else if (event.event_type === "report.generated" && event.data) {
      if (typeof event.data.findings_count === "number") {
        statusUpdate.findings_count = Math.max(
          get().jobStatus?.findings_count ?? 0,
          event.data.findings_count
        );
      }
    } else if (event.event_type === "progress" && event.data) {
      if (typeof event.data.progress === "number") {
        statusUpdate.progress = event.data.progress;
      }
      if (typeof event.data.step === "string") {
        statusUpdate.current_step = event.data.step;
      }
    }

    if (Object.keys(statusUpdate).length > 0) {
      set((state) => ({
        jobStatus: state.jobStatus
          ? { ...state.jobStatus, ...statusUpdate }
          : {
              job_id: event.job_id,
              status: "pending",
              progress: 0,
              competitors_found: 0,
              pages_scraped: 0,
              findings_count: 0,
              ...statusUpdate,
            },
      }));
    }

    // Auto-fetch report on completion
    if (event.event_type === "report.generated" || event.event_type === "job.completed") {
      const { activeJobId } = get();
      if (activeJobId) {
        get().fetchReport(activeJobId);
      }
    }

    if (
      event.event_type === "job.completed" ||
      event.event_type === "job.failed" ||
      event.event_type === "job.cancelled"
    ) {
      get().disconnectSSE();
    }
  },

  setJobStatus: (status: JobStatusResponse) => {
    set({ jobStatus: status });
  },

  setReport: (report: IntelligenceReport) => {
    set({ report });
  },

  setError: (error: string | null) => {
    set({ error });
  },

  fetchJobs: async () => {
    try {
      const res = await listJobs();
      set({ jobs: res.jobs });
    } catch {
      // Silently fail — might be no backend yet
    }
  },

  fetchReport: async (jobId: string) => {
    try {
      const res = await getReport(jobId);
      set({ report: res.report });
    } catch {
      // Report not ready yet or backend unavailable
    }
  },

  cancelActiveJob: async () => {
    const { activeJobId } = get();
    if (!activeJobId) return;
    try {
      await cancelJob(activeJobId);
      set((state) => ({
        jobStatus: state.jobStatus
          ? { ...state.jobStatus, status: "cancelled", error: "Cancelled by user" }
          : null,
      }));
      get().disconnectSSE();
      toast({ variant: "info", title: "Job Cancelled", description: "The job has been cancelled." });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to cancel job";
      toast({ variant: "error", title: "Cancellation Failed", description: message });
    }
  },

  clearActive: () => {
    get().disconnectSSE();
    set({
      activeJobId: null,
      events: [],
      jobStatus: null,
      report: null,
      error: null,
    });
  },

  // ── SSE Connection ─────────────────────────────────────────────────────

  connectSSE: (jobId: string) => {
    get().disconnectSSE();

    const conn = connectJobStream(
      jobId,
      (event) => get().addEvent(event),
      () => {
        // SSE error handled internally
      },
      () => {
        set({ _sseConnection: null });
      }
    );

    set({ _sseConnection: conn });
  },

  disconnectSSE: () => {
    const { _sseConnection } = get();
    if (_sseConnection) {
      _sseConnection.close();
      set({ _sseConnection: null });
    }
  },
}));
