# API Reference

## Base URL

```
http://localhost:8000
```

## Authentication

Not enabled by default. See `docs/SECURITY.md` for optional JWT authentication setup.

## Endpoints

### Health

#### `GET /api/health`

Liveness and readiness probe.

**Response:** `HealthResponse`
```json
{
  "status": "ok",
  "version": "0.2.0",
  "llm_configured": true,
  "scheduler_running": true,
  "active_jobs": 2,
  "total_jobs_completed": 15
}
```

---

### Jobs

#### `POST /api/jobs`

Create a new analysis job and start the pipeline.

**Request:** `CreateJobRequest`
```json
{
  "competitors": [
    {
      "url": "https://notion.so",
      "name": "Notion",
      "focus_areas": ["pricing", "features"]
    },
    {
      "url": "https://obsidian.md"
    }
  ],
  "query": "Compare pricing strategies",
  "schedule": {
    "frequency": "daily"
  }
}
```

**Response:** `CreateJobResponse` (201)
```json
{
  "job_id": "a1b2c3d4...",
  "status": "pending",
  "message": "Job created. Pipeline started."
}
```

**Validation:**
- `competitors`: 1–10 items required
- `url`: Must be http/https, not localhost/private IP
- `query`: Max 10,000 characters
- `schedule.frequency`: `once`, `hourly`, `daily`, `weekly`, `custom`
- `custom` frequency requires `cron_expression`

---

#### `GET /api/jobs`

List all tracked jobs.

**Response:** `JobListResponse`
```json
{
  "jobs": [
    {
      "job_id": "...",
      "status": "completed",
      "progress": 1.0,
      "current_step": "completed",
      "competitors_found": 2,
      "pages_scraped": 12,
      "findings_count": 5,
      "started_at": "2025-01-01T00:00:00Z",
      "completed_at": "2025-01-01T00:05:00Z"
    }
  ],
  "total": 1
}
```

---

#### `GET /api/jobs/{job_id}`

Get status of a single job.

**Response:** `JobStatusResponse`

---

#### `GET /api/jobs/{job_id}/stream`

SSE event stream for real-time job progress.

**Headers:**
- `Last-Event-Id` (optional): Reconnect from this event

**Events:**
```
event: step.started
id: step.started-abc123-def456
data: {"event_id": "...", "event_type": "step.started", "job_id": "...", ...}

event: page.scraped
id: page.scraped-abc123-789
data: {"event_id": "...", "event_type": "page.scraped", "url": "https://...", ...}

event: finding.found
data: {"event_id": "...", "event_type": "finding.found", "finding_id": "...", ...}

event: claim.verified
data: {"event_id": "...", "event_type": "claim.verified", "verified": true, ...}

event: report.generated
data: {"event_id": "...", "event_type": "report.generated", "findings_count": 5, ...}

event: job.completed
data: {"event_id": "...", "event_type": "job.completed", "message": "Pipeline completed"}
```

**Heartbeats:** `:heartbeat` comments sent every 15 seconds to keep connection alive.

---

#### `GET /api/jobs/{job_id}/report`

Retrieve the final report for a completed job.

**Response:** `ReportResponse`
```json
{
  "report": {
    "id": "report-abc123",
    "title": "Intelligence Report: notion.so, obsidian.md",
    "created_at": "...",
    "competitors": [...],
    "findings": [...],
    "comparison_tables": [...],
    "executive_summary": "...",
    "trend_analysis": "...",
    "recommendations": [...],
    "total_sources": 32,
    "verification_passes": 2
  }
}
```

**Errors:**
- 404: Job not found
- 400: Job not yet completed

---

#### `DELETE /api/jobs/{job_id}`

Cancel a running or pending job.

**Response:** `CancelJobResponse`
```json
{
  "job_id": "...",
  "status": "cancelled",
  "message": "Job cancelled"
}
```

**Errors:**
- 404: Job not found
- 400: Job already completed/failed

---

#### `POST /api/jobs/{job_id}/export`

Export the report in the requested format.

**Request:** `ExportRequest`
```json
{
  "format": "pdf",
  "include_citations": true,
  "include_raw_data": false
}
```

**Response:** `ExportResponse`
```json
{
  "job_id": "...",
  "format": "pdf",
  "download_url": "/data/exports/report_abc123_20250101120000.pdf"
}
```

Formats: `json`, `csv`, `markdown`, `pdf`

---

### Analytics

#### `GET /api/stats`

Dashboard aggregate statistics.

**Response:** `DashboardStats`
```json
{
  "total_jobs": 20,
  "completed_jobs": 15,
  "failed_jobs": 3,
  "total_findings": 45,
  "high_confidence_findings": 28,
  "total_competitors_tracked": 8,
  "total_pages_scraped": 150,
  "total_verifications": 30,
  "average_confidence_score": 0.82,
  "jobs_last_7_days": 5,
  "findings_by_category": {"pricing": 12, "features": 18},
  "top_competitors": [{"name": "Notion", "url": "notion.so", "job_count": 8}]
}
```

---

#### `GET /api/trends`

Trend data for charts.

**Query Parameters:**
- `metric`: `findings_count`, `pages_scraped`, `jobs_created`, `confidence_score` (default: `findings`)
- `days`: 1–365 (default: `30`)

**Response:** `TrendResponse`
```json
{
  "metric": "findings_count",
  "data_points": [
    {"date": "2025-01-01", "value": 12.0},
    {"date": "2025-01-02", "value": 8.0}
  ]
}
```

---

### Schedules

#### `GET /api/schedules`

List all scheduled jobs.

**Response:** `ScheduledJobListResponse`

---

#### `POST /api/schedules`

Create a new scheduled job.

**Request:** `CreateJobRequest` (with `schedule` required, frequency must not be `once`)

**Response:** `ScheduledJobResponse` (201)

---

#### `PATCH /api/schedules/{schedule_id}`

Update a schedule (enable/disable, change frequency).

**Request:** `UpdateScheduleRequest`
```json
{
  "enabled": false,
  "frequency": "weekly"
}
```

**Response:** `ScheduledJobResponse`

---

#### `DELETE /api/schedules/{schedule_id}`

Delete a scheduled job.

**Response:** `{"status": "deleted", "schedule_id": "..."}`

---

## Rate Limiting

All endpoints (except health) are rate-limited:

| Category | Limit | Window |
|----------|-------|--------|
| General | 100 requests | 60 seconds |
| Job creation | 10 requests | 60 seconds |

**Headers:**
- `X-RateLimit-Limit`: Maximum requests in window
- `X-RateLimit-Remaining`: Requests remaining
- `X-RateLimit-Reset`: Seconds until window resets
- `Retry-After`: Seconds to wait (on 429)
