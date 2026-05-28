"use client";

import { useEffect } from "react";
import { useParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useJobStore } from "@/stores/jobStore";
import { ReportView } from "@/components/ReportView";
import { ProgressConsole } from "@/components/ProgressConsole";
import { ErrorBoundary } from "@/components/ErrorBoundary";

export default function ReportPage() {
  const params = useParams<{ jobId: string }>();
  const jobId = params.jobId;

  const { activeJobId, report, events, jobStatus, isDemoMode, setActiveJob, cancelActiveJob, disconnectSSE } =
    useJobStore();

  useEffect(() => {
    if (jobId) {
      setActiveJob(jobId);
    }
    return () => {
      disconnectSSE();
    };
  }, [jobId, setActiveJob, disconnectSSE]);

  const isRunning = jobStatus && !["completed", "failed", "cancelled"].includes(jobStatus.status);

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 py-6 sm:py-8">
      {/* Breadcrumb */}
      <div className="mb-6">
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-sm text-text-secondary hover:text-accent transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Dashboard
        </Link>
      </div>

      {/* Report Header */}
      <div className="mb-6">
        <h2 className="text-xl sm:text-2xl font-bold text-text-primary">
          Intelligence Report
        </h2>
        <p className="mt-1 text-sm text-text-secondary">
          Job ID: {jobId}
        </p>
      </div>

      <div className="space-y-6">
        <ErrorBoundary>
          <ProgressConsole
            events={events}
            jobStatus={jobStatus}
            isDemoMode={isDemoMode}
            onCancel={isRunning ? cancelActiveJob : undefined}
          />
        </ErrorBoundary>

        {report ? (
          <ErrorBoundary>
            <ReportView report={report} jobId={jobId} />
          </ErrorBoundary>
        ) : (
          <div className="rounded-xl border border-border bg-bg-card/80 backdrop-blur-sm p-8 text-center">
            <p className="text-text-secondary">
              No report available yet. The analysis may still be in progress.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
