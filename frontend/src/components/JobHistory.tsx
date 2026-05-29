"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Eye, XCircle } from "lucide-react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog";
import { toast } from "@/components/ui/toast";
import { cancelJob } from "@/lib/api";
import { formatDate, statusColor, formatProgress } from "@/lib/utils";
import type { JobStatusResponse } from "@/types";

interface JobHistoryProps {
  jobs: JobStatusResponse[];
  activeJobId: string | null;
  onSelectJob?: (jobId: string) => void;
  onJobCancelled?: (jobId: string) => void;
  filter?: string;
}

function StatusBadge({ status }: { status: string }) {
  const c = statusColor(status);
  return (
    <span
      className={`inline-flex items-center gap-1.5 text-xs font-medium ${c.text}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${c.dot}`} />
      {c.label}
    </span>
  );
}

export function JobHistory({
  jobs,
  activeJobId,
  onSelectJob,
  onJobCancelled,
  filter = "all",
}: JobHistoryProps) {
  const router = useRouter();
  const [cancelTarget, setCancelTarget] = useState<JobStatusResponse | null>(
    null
  );
  const [cancelling, setCancelling] = useState(false);

  const filteredJobs =
    filter === "all" ? jobs : jobs.filter((j) => j.status === filter);

  async function handleCancel() {
    if (!cancelTarget) return;
    setCancelling(true);
    try {
      await cancelJob(cancelTarget.job_id);
      toast({
        variant: "info",
        title: "Job Cancelled",
        description: `Job ${cancelTarget.job_id.slice(0, 8)}... has been cancelled.`,
      });
      onJobCancelled?.(cancelTarget.job_id);
      setCancelTarget(null);
    } catch (err) {
      toast({
        variant: "error",
        title: "Cancellation Failed",
        description:
          err instanceof Error ? err.message : "Could not cancel the job.",
      });
    } finally {
      setCancelling(false);
    }
  }

  function isActive(status: string): boolean {
    return [
      "pending",
      "scraping",
      "analyzing",
      "verifying",
      "generating_report",
    ].includes(status);
  }

  if (filteredJobs.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Job History</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-text-muted text-center py-8">
            {filter === "all"
              ? "No jobs yet. Create your first analysis."
              : `No ${filter} jobs found.`}
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Job History</CardTitle>
            <span className="text-xs text-text-muted">
              {filteredJobs.length} jobs
            </span>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="divide-y divide-border">
            {filteredJobs.map((job) => {
              const isSelected = job.job_id === activeJobId;
              const isJobActive = isActive(job.status);
              return (
                <div
                  key={job.job_id}
                  className={`flex items-center gap-4 px-6 py-3 transition-colors cursor-pointer ${
                    isSelected
                      ? "bg-accent-subtle"
                      : "hover:bg-bg-secondary"
                  }`}
                  onClick={() => onSelectJob?.(job.job_id)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      onSelectJob?.(job.job_id);
                    }
                  }}
                  aria-label={`View job ${job.job_id}`}
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <StatusBadge status={job.status} />
                      <span className="text-xs text-text-muted font-mono truncate">
                        {job.job_id.slice(0, 12)}...
                      </span>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-text-secondary">
                      <span>{job.competitors_found} competitors</span>
                      <span>{job.findings_count} findings</span>
                      <span>{formatDate(job.started_at)}</span>
                    </div>
                    {isJobActive && (
                      <Progress
                        value={job.progress}
                        showLabel
                        className="mt-2 max-w-xs"
                      />
                    )}
                    {job.error && (
                      <p className="mt-1 text-xs text-error truncate">
                        {job.error}
                      </p>
                    )}
                  </div>

                  <div className="flex items-center gap-1 shrink-0">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        router.push(`/report/${job.job_id}`);
                      }}
                      aria-label={`View report for job ${job.job_id}`}
                    >
                      <Eye className="h-4 w-4" />
                    </Button>
                    {isJobActive && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          setCancelTarget(job);
                        }}
                        aria-label={`Cancel job ${job.job_id}`}
                      >
                        <XCircle className="h-4 w-4 text-error" />
                      </Button>
                    )}
                    {isSelected && (
                      <div className="ml-1 h-2 w-2 rounded-full bg-accent" />
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      <Dialog
        open={!!cancelTarget}
        onOpenChange={(open) => !open && setCancelTarget(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Cancel Job</DialogTitle>
            <DialogDescription>
              Are you sure you want to cancel this job? Progress will be lost.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="secondary">Keep Running</Button>
            </DialogClose>
            <Button
              variant="danger"
              onClick={handleCancel}
              isLoading={cancelling}
            >
              Cancel Job
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
