/**
 * API client for the Market Intelligence Agent backend.
 * All requests go directly to the FastAPI server (no Next.js API routes).
 */

import type {
  CreateJobRequest,
  CreateJobResponse,
  JobStatusResponse,
  JobListResponse,
  ReportResponse,
  HealthResponse,
  CancelJobResponse,
  ExportRequest,
  ExportResponse,
  DashboardStats,
  TrendResponse,
  ScheduledJobResponse,
  ScheduledJobListResponse,
  UpdateScheduleRequest,
  ErrorResponse,
} from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  detail?: string;

  constructor(message: string, status: number, detail?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

/** Human-friendly error messages by HTTP status. */
function friendlyMessage(status: number, body: string): string {
  // Try to parse ErrorResponse from body
  try {
    const parsed = JSON.parse(body) as ErrorResponse;
    if (parsed.error) return parsed.error;
  } catch {
    // not JSON, use raw body
  }

  switch (status) {
    case 0:
      return "Cannot reach backend. Is the server running? Start with: docker-compose up";
    case 404:
      return "The requested resource was not found. It may have been removed or the job ID is invalid.";
    case 409:
      return "This job has already been completed or cancelled.";
    case 422:
      return "Invalid request data. Check that all URLs are valid and required fields are filled in.";
    case 500:
      return "Internal server error. The backend encountered an unexpected problem. Check backend logs for details.";
    case 502:
    case 503:
      return "Backend not running. Start with: docker-compose up or python -m backend.main";
    default:
      return body || `Request failed with status ${status}`;
  }
}

async function request<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE}${path}`;

  let res: Response;
  try {
    res = await fetch(url, {
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
      ...options,
    });
  } catch (err) {
    // Network error — backend is unreachable
    const msg =
      err instanceof TypeError && err.message.includes("fetch")
        ? "Backend not running. Start with: docker-compose up or python -m backend.main"
        : `Network error: ${err instanceof Error ? err.message : String(err)}`;
    throw new ApiError(msg, 0);
  }

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    const detail = (() => {
      try {
        const parsed = JSON.parse(body) as ErrorResponse;
        return parsed.detail;
      } catch {
        return undefined;
      }
    })();
    throw new ApiError(friendlyMessage(res.status, body), res.status, detail);
  }

  if (res.status === 204) {
    return undefined as T;
  }
  const text = await res.text();
  if (!text) {
    return undefined as T;
  }
  return JSON.parse(text) as T;
}

// ── Jobs ──────────────────────────────────────────────────────────────────

export async function createJob(
  payload: CreateJobRequest
): Promise<CreateJobResponse> {
  return request<CreateJobResponse>("/api/jobs", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getJobStatus(
  jobId: string
): Promise<JobStatusResponse> {
  return request<JobStatusResponse>(`/api/jobs/${jobId}`);
}

export async function listJobs(): Promise<JobListResponse> {
  return request<JobListResponse>("/api/jobs");
}

export async function getReport(jobId: string): Promise<ReportResponse> {
  return request<ReportResponse>(`/api/jobs/${jobId}/report`);
}

export async function cancelJob(
  jobId: string
): Promise<CancelJobResponse> {
  return request<CancelJobResponse>(`/api/jobs/${jobId}`, {
    method: "DELETE",
  });
}

export async function exportReport(
  jobId: string,
  payload: ExportRequest
): Promise<ExportResponse> {
  return request<ExportResponse>(`/api/jobs/${jobId}/export`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// ── Health ────────────────────────────────────────────────────────────────

export async function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/api/health");
}

// ── Dashboard Analytics ──────────────────────────────────────────────────

export async function getStats(): Promise<DashboardStats> {
  return request<DashboardStats>("/api/stats");
}

export async function getTrends(
  metric: string = "findings",
  days: number = 30
): Promise<TrendResponse> {
  return request<TrendResponse>(
    `/api/trends?metric=${encodeURIComponent(metric)}&days=${days}`
  );
}

// ── Scheduled Jobs ───────────────────────────────────────────────────────

export async function listSchedules(): Promise<ScheduledJobListResponse> {
  return request<ScheduledJobListResponse>("/api/schedules");
}

export async function createSchedule(
  payload: CreateJobRequest
): Promise<ScheduledJobResponse> {
  return request<ScheduledJobResponse>("/api/schedules", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateSchedule(
  scheduleId: string,
  payload: UpdateScheduleRequest
): Promise<ScheduledJobResponse> {
  return request<ScheduledJobResponse>(`/api/schedules/${scheduleId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deleteSchedule(scheduleId: string): Promise<void> {
  return request<void>(`/api/schedules/${scheduleId}`, {
    method: "DELETE",
  });
}

export { API_BASE };
