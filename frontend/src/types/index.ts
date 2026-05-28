/**
 * TypeScript mirror of contracts/types.ts for the Next.js frontend.
 * Keep in sync with the Python contracts.
 */

// ── Enums ────────────────────────────────────────────────────────────────

export type JobStatus =
  | "pending"
  | "scraping"
  | "analyzing"
  | "verifying"
  | "generating_report"
  | "completed"
  | "failed"
  | "cancelled";

export type ConfidenceLevel = "high" | "medium" | "low" | "very_low";

export type ScheduleFrequency = "once" | "hourly" | "daily" | "weekly" | "custom";

export type ExportFormat = "json" | "csv" | "markdown" | "pdf";

// ── Competitor ───────────────────────────────────────────────────────────

export interface CompetitorInput {
  url: string;
  name?: string;
  focus_areas: string[];
}

export interface ScrapedPage {
  url: string;
  page_type: string;
  title?: string;
  content_hash: string;
  scraped_at: string;
  raw_text: string;
}

export interface PricingPlan {
  name: string;
  price?: string;
  billing_period?: string;
  features: string[];
  highlighted: boolean;
}

export interface PricingData {
  plans: PricingPlan[];
  currency: string;
  has_free_tier: boolean;
  enterprise_tier: boolean;
  source_url: string;
  scraped_at: string;
}

export interface FeatureData {
  name: string;
  description?: string;
  category?: string;
  competitor_advantage?: string;
  source_url: string;
}

export interface TeamMember {
  name: string;
  role?: string;
  linkedin_url?: string;
}

export interface TeamData {
  team_size?: string;
  key_members: TeamMember[];
  recent_hires: TeamMember[];
  source_url: string;
}

export interface NewsItem {
  title: string;
  url: string;
  date?: string;
  summary?: string;
  source: string;
}

export interface CompetitorData {
  id: string;
  name: string;
  url: string;
  logo_url?: string;
  scraped_pages: ScrapedPage[];
  pricing?: PricingData;
  features: FeatureData[];
  team_info?: TeamData;
  recent_news: NewsItem[];
  last_updated: string;
}

// ── Citation & Confidence ────────────────────────────────────────────────

export interface Citation {
  url: string;
  title?: string;
  quote: string;
  accessed_at: string;
  confidence: ConfidenceLevel;
}

// ── Findings ─────────────────────────────────────────────────────────────

export interface Finding {
  id: string;
  title: string;
  summary: string;
  category: string;
  confidence: ConfidenceLevel;
  confidence_score: number;
  citations: Citation[];
  competitor_ids: string[];
  impact?: string;
  recommendation?: string;
}

export interface ComparisonRow {
  dimension: string;
  values: Record<string, string>;
  winner?: string;
}

export interface ComparisonTable {
  title: string;
  dimensions: string[];
  rows: ComparisonRow[];
  competitor_ids: string[];
}

// ── Report ───────────────────────────────────────────────────────────────

export interface IntelligenceReport {
  id: string;
  title: string;
  created_at: string;
  competitors: CompetitorData[];
  findings: Finding[];
  comparison_tables: ComparisonTable[];
  executive_summary: string;
  trend_analysis?: string;
  recommendations: string[];
  total_sources: number;
  verification_passes: number;
}

// ── API Request/Response ─────────────────────────────────────────────────

export interface ScheduleConfig {
  frequency: ScheduleFrequency;
  cron_expression?: string;
  next_run?: string;
}

export interface CreateJobRequest {
  competitors: CompetitorInput[];
  query?: string;
  schedule?: ScheduleConfig;
}

export interface CreateJobResponse {
  job_id: string;
  status: JobStatus;
  message: string;
}

export interface JobStatusResponse {
  job_id: string;
  status: JobStatus;
  progress: number;
  current_step?: string;
  competitors_found: number;
  pages_scraped: number;
  findings_count: number;
  started_at?: string;
  completed_at?: string;
  error?: string;
}

export interface ReportResponse {
  report: IntelligenceReport;
}

export interface JobListResponse {
  jobs: JobStatusResponse[];
  total: number;
}

export interface HealthResponse {
  status: string;
  version: string;
  llm_configured: boolean;
  scheduler_running: boolean;
  active_jobs: number;
  total_jobs_completed: number;
}

// ── Job Cancellation ─────────────────────────────────────────────────────

export interface CancelJobResponse {
  job_id: string;
  status: JobStatus;
  message: string;
}

// ── Export ───────────────────────────────────────────────────────────────

export interface ExportRequest {
  format: ExportFormat;
  include_citations: boolean;
  include_raw_data: boolean;
}

export interface ExportResponse {
  job_id: string;
  format: ExportFormat;
  content?: string;
  download_url?: string;
}

// ── Scheduled Jobs ───────────────────────────────────────────────────────

export interface ScheduledJobResponse {
  schedule_id: string;
  job_config: CreateJobRequest;
  frequency: ScheduleFrequency;
  cron_expression?: string;
  next_run?: string;
  last_run?: string;
  last_job_id?: string;
  enabled: boolean;
  created_at: string;
}

export interface ScheduledJobListResponse {
  schedules: ScheduledJobResponse[];
  total: number;
}

export interface UpdateScheduleRequest {
  enabled?: boolean;
  frequency?: ScheduleFrequency;
  cron_expression?: string;
}

// ── Dashboard Analytics ─────────────────────────────────────────────────

export interface DashboardStats {
  total_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  total_findings: number;
  high_confidence_findings: number;
  total_competitors_tracked: number;
  total_pages_scraped: number;
  total_verifications: number;
  average_confidence_score: number;
  jobs_last_7_days: number;
  findings_by_category: Record<string, number>;
  top_competitors: Array<{ name: string; url: string; job_count: number }>;
}

export interface TrendDataPoint {
  date: string;
  value: number;
  label?: string;
}

export interface TrendResponse {
  metric: string;
  data_points: TrendDataPoint[];
}

// ── Error Response ───────────────────────────────────────────────────────

export interface ErrorResponse {
  error: string;
  detail?: string;
  status_code: number;
}

// ── SSE Events ───────────────────────────────────────────────────────────

export type EventType =
  | "job.started"
  | "job.completed"
  | "job.failed"
  | "job.cancelled"
  | "step.started"
  | "step.completed"
  | "step.failed"
  | "page.scraped"
  | "scraping.complete"
  | "finding.found"
  | "comparison.generated"
  | "claim.verified"
  | "claim.flagged"
  | "verification.complete"
  | "report.generated"
  | "log"
  | "progress"
  | "heartbeat";

export interface AgentEvent {
  event_id: string;
  event_type: EventType;
  job_id: string;
  agent_name: string;
  timestamp: string;
  message: string;
  data?: Record<string, unknown>;
}
