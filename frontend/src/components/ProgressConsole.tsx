"use client";

import { useEffect, useRef, useState } from "react";
import {
  Play,
  CheckCircle,
  AlertTriangle,
  Globe,
  Search,
  ShieldCheck,
  FileText,
  ChevronDown,
  ChevronRight,
  XCircle,
  Clock,
} from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog";
import { formatDate } from "@/lib/utils";
import type { AgentEvent, JobStatusResponse, EventType } from "@/types";

interface ProgressConsoleProps {
  events: AgentEvent[];
  jobStatus: JobStatusResponse | null;
  isDemoMode: boolean;
  onCancel?: () => void;
}

function getEventIcon(eventType: EventType): React.ReactNode {
  const cls = "h-3.5 w-3.5 shrink-0";
  switch (eventType) {
    case "job.started":
      return <Play className={`${cls} text-accent`} />;
    case "job.completed":
      return <CheckCircle className={`${cls} text-success`} />;
    case "job.failed":
      return <AlertTriangle className={`${cls} text-error`} />;
    case "job.cancelled":
      return <XCircle className={`${cls} text-text-muted`} />;
    case "step.started":
      return <Play className={`${cls} text-accent`} />;
    case "step.completed":
      return <CheckCircle className={`${cls} text-accent`} />;
    case "step.failed":
      return <AlertTriangle className={`${cls} text-error`} />;
    case "page.scraped":
      return <Globe className={`${cls} text-blue-400`} />;
    case "scraping.complete":
      return <CheckCircle className={`${cls} text-blue-400`} />;
    case "finding.found":
      return <Search className={`${cls} text-warning`} />;
    case "comparison.generated":
      return <FileText className={`${cls} text-purple-400`} />;
    case "claim.verified":
      return <ShieldCheck className={`${cls} text-success`} />;
    case "claim.flagged":
      return <AlertTriangle className={`${cls} text-warning`} />;
    case "verification.complete":
      return <ShieldCheck className={`${cls} text-success`} />;
    case "report.generated":
      return <FileText className={`${cls} text-accent`} />;
    case "log":
      return <span className="h-3.5 w-3.5 flex items-center justify-center text-text-muted shrink-0">-</span>;
    case "progress":
      return <span className="h-3.5 w-3.5 flex items-center justify-center text-accent shrink-0">%</span>;
    default:
      return <Play className={`${cls} text-text-muted`} />;
  }
}

function getEventColor(eventType: EventType): string {
  switch (eventType) {
    case "job.completed":
    case "step.completed":
    case "claim.verified":
    case "verification.complete":
      return "text-success";
    case "job.failed":
    case "step.failed":
      return "text-error";
    case "job.cancelled":
      return "text-text-muted";
    case "finding.found":
    case "claim.flagged":
      return "text-warning";
    default:
      return "text-text-secondary";
  }
}

function formatTime(timestamp: string): string {
  try {
    return new Date(timestamp).toLocaleTimeString("en-US", {
      hour12: false,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return "??:??:??";
  }
}

function getElapsed(startedAt?: string): string {
  if (!startedAt) return "";
  const elapsed = Date.now() - new Date(startedAt).getTime();
  const secs = Math.floor(elapsed / 1000);
  if (secs < 60) return `${secs}s`;
  const mins = Math.floor(secs / 60);
  const remainSecs = secs % 60;
  return `${mins}m ${remainSecs}s`;
}

function getStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    pending: "Queued",
    scraping: "Scraping Competitors",
    analyzing: "Analyzing Data",
    verifying: "Verifying Claims",
    generating_report: "Generating Report",
    completed: "Complete",
    failed: "Failed",
    cancelled: "Cancelled",
  };
  return labels[status] ?? status;
}

// Group consecutive page.scraped events for collapsible display
interface EventGroup {
  type: "single" | "grouped";
  events: AgentEvent[];
  label?: string;
}

function groupEvents(events: AgentEvent[]): EventGroup[] {
  const groups: EventGroup[] = [];
  let currentGroup: AgentEvent[] = [];

  for (const event of events) {
    if (event.event_type === "page.scraped") {
      currentGroup.push(event);
    } else {
      if (currentGroup.length > 0) {
        groups.push({
          type: "grouped",
          events: currentGroup,
          label: `Scraped ${currentGroup.length} page${currentGroup.length > 1 ? "s" : ""}`,
        });
        currentGroup = [];
      }
      groups.push({ type: "single", events: [event] });
    }
  }
  if (currentGroup.length > 0) {
    groups.push({
      type: "grouped",
      events: currentGroup,
      label: `Scraped ${currentGroup.length} page${currentGroup.length > 1 ? "s" : ""}`,
    });
  }
  return groups;
}

function EventGroupView({ group }: { group: EventGroup }) {
  const [expanded, setExpanded] = useState(false);

  if (group.type === "single") {
    const event = group.events[0];
    return (
      <div className="flex items-start gap-2 py-0.5">
        <span className="shrink-0 text-text-muted tabular-nums text-[10px] mt-0.5 w-14">
          {formatTime(event.timestamp)}
        </span>
        {getEventIcon(event.event_type)}
        <span className={getEventColor(event.event_type)}>
          {event.message}
        </span>
      </div>
    );
  }

  return (
    <div>
      <button
        className="flex items-center gap-2 py-0.5 w-full text-left hover:bg-bg-card-hover rounded px-1 -mx-1 transition-colors"
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
        aria-label={`${expanded ? "Collapse" : "Expand"} ${group.label}`}
      >
        {expanded ? (
          <ChevronDown className="h-3 w-3 text-text-muted shrink-0" />
        ) : (
          <ChevronRight className="h-3 w-3 text-text-muted shrink-0" />
        )}
        <Globe className="h-3.5 w-3.5 text-blue-400 shrink-0" />
        <span className="text-text-secondary">{group.label}</span>
      </button>
      {expanded && (
        <div className="ml-8 border-l border-border pl-3 mt-1 space-y-0.5">
          {group.events.map((event, i) => (
            <div key={event.event_id || i} className="flex items-start gap-2 py-0.5">
              <span className="shrink-0 text-text-muted tabular-nums text-[10px] mt-0.5 w-14">
                {formatTime(event.timestamp)}
              </span>
              <Globe className="h-3 w-3 text-blue-400/60 shrink-0 mt-0.5" />
              <span className="text-text-secondary text-xs">{event.message}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function ProgressConsole({
  events,
  jobStatus,
  isDemoMode,
  onCancel,
}: ProgressConsoleProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [cancelConfirm, setCancelConfirm] = useState(false);
  const [elapsed, setElapsed] = useState("");

  // Auto-scroll to bottom on new events
  useEffect(() => {
    const el = scrollRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [events]);

  // Update elapsed time
  const startedAt = jobStatus?.started_at;
  const statusStr = jobStatus?.status;

  useEffect(() => {
    if (!startedAt) return;
    const isRunning = statusStr && !["completed", "failed", "cancelled"].includes(statusStr);
    if (!isRunning) return;

    const interval = setInterval(() => {
      setElapsed(getElapsed(startedAt));
    }, 1000);
    setElapsed(getElapsed(startedAt));
    return () => clearInterval(interval);
  }, [startedAt, statusStr]);

  const isRunning =
    jobStatus &&
    !["completed", "failed", "cancelled"].includes(jobStatus.status);
  const hasFailed = jobStatus?.status === "failed";
  const isCancelled = jobStatus?.status === "cancelled";
  const groupedEvents = groupEvents(events);

  return (
    <>
      <Card className="overflow-hidden">
        {/* Header */}
        <CardHeader className="py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CardTitle className="text-sm">Agent Console</CardTitle>
              {isDemoMode && (
                <span className="rounded-full bg-accent/20 px-2 py-0.5 text-xs text-accent">
                  Demo
                </span>
              )}
              {isRunning && (
                <span className="flex items-center gap-1.5 text-xs text-text-secondary">
                  <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent" />
                  Running
                </span>
              )}
            </div>
            <div className="flex items-center gap-3">
              {elapsed && isRunning && (
                <span className="flex items-center gap-1 text-xs text-text-muted">
                  <Clock className="h-3 w-3" />
                  {elapsed}
                </span>
              )}
              {jobStatus && (
                <span
                  className={`text-xs font-medium ${
                    hasFailed
                      ? "text-error"
                      : isCancelled
                      ? "text-text-muted"
                      : "text-text-secondary"
                  }`}
                >
                  {getStatusLabel(jobStatus.status)}
                </span>
              )}
            </div>
          </div>
        </CardHeader>

        {/* Progress Bar */}
        <Progress
          value={jobStatus?.progress ?? 0}
          variant={hasFailed || isCancelled ? "error" : "default"}
          className="px-0"
        />

        {/* Event Log */}
        <CardContent>
          <div
            ref={scrollRef}
            className="max-h-80 overflow-y-auto font-mono text-xs"
          >
            {events.length === 0 ? (
              <div className="space-y-3 py-2">
                {[...Array(6)].map((_, i) => (
                  <div key={i} className="flex items-center gap-3">
                    <Skeleton className="h-3 w-14" />
                    <Skeleton className="h-3.5 w-3.5 rounded-full" />
                    <Skeleton
                      className="h-3"
                      style={{ width: `${50 + (i * 13) % 40}%` }}
                    />
                  </div>
                ))}
              </div>
            ) : (
              <div className="space-y-0.5">
                {groupedEvents.map((group, i) => (
                  <EventGroupView key={i} group={group} />
                ))}
              </div>
            )}
          </div>
        </CardContent>

        {/* Stats Footer */}
        {jobStatus && (
          <div className="flex items-center gap-4 border-t border-border px-6 py-2.5 text-xs text-text-secondary">
            <span>
              <span className="text-text-primary font-medium">
                {jobStatus.competitors_found}
              </span>{" "}
              competitors
            </span>
            <span>
              <span className="text-text-primary font-medium">
                {jobStatus.pages_scraped}
              </span>{" "}
              pages scraped
            </span>
            <span>
              <span className="text-text-primary font-medium">
                {jobStatus.findings_count}
              </span>{" "}
              findings
            </span>
            {jobStatus.current_step && (
              <span className="ml-auto capitalize text-text-muted">
                Step: {jobStatus.current_step.replace(/_/g, " ")}
              </span>
            )}
            {isRunning && onCancel && (
              <Button
                variant="danger"
                size="sm"
                onClick={() => setCancelConfirm(true)}
                className="ml-auto"
              >
                <XCircle className="h-3.5 w-3.5" />
                Cancel
              </Button>
            )}
          </div>
        )}
      </Card>

      <Dialog open={cancelConfirm} onOpenChange={setCancelConfirm}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Cancel Job</DialogTitle>
            <DialogDescription>
              Are you sure you want to cancel this job? Progress will be lost and this action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="secondary">Keep Running</Button>
            </DialogClose>
            <Button
              variant="danger"
              onClick={() => {
                setCancelConfirm(false);
                onCancel?.();
              }}
            >
              Cancel Job
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
