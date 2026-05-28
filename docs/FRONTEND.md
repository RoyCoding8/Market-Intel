# Frontend Architecture

## Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Framework | Next.js | 16.2.6 |
| UI Library | React | 19.2.4 |
| State Management | Zustand | 5.x |
| Styling | Tailwind CSS | 4.x |
| Charts | Recharts | 3.x |
| UI Primitives | Radix UI | Latest |
| Testing | Vitest + Testing Library | Latest |

## File Structure

```
frontend/src/
├── app/
│   ├── layout.tsx          # Root layout (header, footer, toaster)
│   ├── page.tsx            # Dashboard page (main view)
│   ├── report/[jobId]/
│   │   └── page.tsx        # Individual report page
│   └── globals.css         # Tailwind base + custom CSS variables
├── components/
│   ├── ui/                 # Reusable primitives (button, card, dialog, etc.)
│   ├── JobCreator.tsx      # Job creation form
│   ├── ProgressConsole.tsx # Real-time event log with progress bar
│   ├── ReportView.tsx      # Full report display with tabs
│   ├── FindingCard.tsx     # Individual finding card
│   ├── ComparisonTable.tsx # Comparison table component
│   ├── ExportButton.tsx    # Report export (JSON/CSV/MD/PDF)
│   ├── StatsCards.tsx      # Dashboard statistics cards
│   ├── TrendsChart.tsx     # Trend data chart
│   ├── CategoryBreakdown.tsx # Findings by category
│   ├── JobHistory.tsx      # Job list with status indicators
│   ├── ScheduleCreator.tsx # Recurring schedule form
│   ├── ScheduleList.tsx    # Schedule management list
│   └── ErrorBoundary.tsx   # React error boundary
├── stores/
│   └── jobStore.ts         # Zustand store (single source of truth)
├── lib/
│   ├── api.ts              # HTTP client for backend API
│   ├── sse.ts              # SSE client for event streaming
│   ├── utils.ts            # Utility functions (cn, formatDate, etc.)
│   └── demoData.ts         # Pre-populated demo data
└── types/
    └── index.ts            # TypeScript type definitions (mirrors contracts/)
```

## State Management

Single Zustand store (`jobStore.ts`) manages all application state:

```typescript
interface JobStore {
  // Active job
  activeJobId: string | null;
  events: AgentEvent[];
  jobStatus: JobStatusResponse | null;
  report: IntelligenceReport | null;

  // All jobs
  jobs: JobStatusResponse[];

  // UI state
  isLoading: boolean;
  error: string | null;
  isDemoMode: boolean;

  // SSE connection
  _sseConnection: SSEConnection | null;
}
```

### State Updates from SSE Events

The `addEvent` action processes incoming SSE events and updates job status:

| Event Type | Status Update |
|-----------|---------------|
| `step.started` + "scraping" | `status: "scraping"`, `progress: 0.1` |
| `step.started` + "analyzing" | `status: "analyzing"`, `progress: 0.35` |
| `step.started` + "verifying" | `status: "verifying"`, `progress: 0.65` |
| `step.started` + "reporting" | `status: "generating_report"`, `progress: 0.85` |
| `page.scraped` | `pages_scraped++` |
| `finding.found` | `findings_count++` |
| `job.completed` | `status: "completed"`, `progress: 1.0` |
| `job.failed` | `status: "failed"` |
| `job.cancelled` | `status: "cancelled"` |

## SSE Client (`lib/sse.ts`)

Connects to `GET /api/jobs/{jobId}/stream`:

1. Creates `EventSource` connection
2. Registers `addEventListener` for every known event type (not just `onmessage`)
3. Parses JSON data from each event
4. Filters out heartbeat events
5. Dispatches to callback
6. Handles reconnection (EventSource auto-reconnects on transient errors)
7. Only closes permanently on `EventSource.CLOSED` state

### Why addEventListener instead of onmessage

The backend uses `sse-starlette`'s `EventSourceResponse`, which sends named events:
```
event: job.started
data: {"event_type": "job.started", ...}
```

The browser's `EventSource.onmessage` only receives unnamed events. Named events require `addEventListener(eventType, handler)`. Without this, all events would be silently dropped.

## Demo Mode

On first load (no real jobs), the frontend displays pre-populated demo data:
- A completed Notion vs Obsidian comparison report
- Simulated event timeline
- All UI components render with demo data

This allows users to see the full UI before connecting a real backend.

## API Client (`lib/api.ts`)

Typed HTTP client with:
- Automatic `Content-Type: application/json` header
- Friendly error messages by HTTP status code
- `ApiError` class with status code and detail
- Network error detection (backend unreachable)

### Error Handling

```typescript
// Network error
throw new ApiError("Backend not running. Start with: docker-compose up", 0);

// HTTP 422
throw new ApiError("Invalid request data. Check URLs...", 422);

// HTTP 500
throw new ApiError("Internal server error...", 500);
```

## Styling

Tailwind CSS 4 with custom CSS variables for theming:
- `--color-bg-primary`, `--color-bg-card` — Background colors
- `--color-text-primary`, `--color-text-secondary` — Text colors
- `--color-accent` — Primary accent color
- `--color-success`, `--color-warning`, `--color-error` — Status colors

All components use the `cn()` utility (clsx + tailwind-merge) for conditional class merging.

## Testing

Vitest with jsdom environment:
- `src/__tests__/store.test.ts` — Store logic
- `src/__tests__/sse.test.ts` — SSE parsing
- `src/__tests__/api.test.ts` — API client
- `src/__tests__/utils.test.ts` — Utility functions
- `src/__tests__/components/` — Component tests

Run with: `npm test` or `npm run test:watch`
