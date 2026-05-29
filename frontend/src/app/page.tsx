"use client";

import { useEffect, useState } from "react";
import { useJobStore } from "@/stores/jobStore";
import { StatsCards } from "@/components/StatsCards";
import { TrendsChart } from "@/components/TrendsChart";
import { CategoryBreakdown } from "@/components/CategoryBreakdown";
import { JobCreator } from "@/components/JobCreator";
import { ProgressConsole } from "@/components/ProgressConsole";
import { ReportView } from "@/components/ReportView";
import { JobHistory } from "@/components/JobHistory";
import { ScheduleCreator } from "@/components/ScheduleCreator";
import { ScheduleList } from "@/components/ScheduleList";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Plus,
  History,
  Clock,
} from "lucide-react";

export default function DashboardPage() {
  const {
    activeJobId,
    events,
    jobStatus,
    report,
    jobs,
    isLoading,
    error,
    isDemoMode,
    loadDemoData,
    fetchJobs,
    setActiveJob,
    cancelActiveJob,
  } = useJobStore();

  const [activeTab, setActiveTab] = useState("new-analysis");
  const [scheduleListKey, setScheduleListKey] = useState(0);

  // Load demo data only if no real jobs exist
  useEffect(() => {
    fetchJobs().then(() => {
      const { jobs, isDemoMode } = useJobStore.getState();
      if (jobs.length === 0 && isDemoMode) {
        loadDemoData();
      }
    });
  }, [loadDemoData, fetchJobs]);

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 py-6 sm:py-8">
      {/* Page Title */}
      <div className="mb-6">
        <h2 className="text-xl sm:text-2xl font-bold text-text-primary">
          Intelligence Dashboard
        </h2>
        <p className="mt-1 text-sm text-text-secondary">
          Create analysis jobs, monitor progress, and review competitive intelligence reports
        </p>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="mb-6 rounded-lg border border-error/20 bg-error-subtle px-4 py-3 text-sm text-error">
          <span className="font-medium">Error:</span> {error}
        </div>
      )}

      {/* Stats Cards */}
      <ErrorBoundary>
        <StatsCards />
      </ErrorBoundary>

      {/* Charts Row */}
      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <ErrorBoundary>
          <TrendsChart />
        </ErrorBoundary>
        <ErrorBoundary>
          <CategoryBreakdown />
        </ErrorBoundary>
      </div>

      {/* Main Content Area */}
      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-3">
        {/* Left Column: Tabs */}
        <div className="xl:col-span-2">
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="w-full sm:w-auto">
              <TabsTrigger value="new-analysis">
                <Plus className="h-4 w-4 mr-1.5 hidden sm:inline" />
                New Analysis
              </TabsTrigger>
              <TabsTrigger value="recent-jobs">
                <History className="h-4 w-4 mr-1.5 hidden sm:inline" />
                Recent Jobs
              </TabsTrigger>
              <TabsTrigger value="scheduled">
                <Clock className="h-4 w-4 mr-1.5 hidden sm:inline" />
                Scheduled
              </TabsTrigger>
            </TabsList>

            {/* New Analysis Tab */}
            <TabsContent value="new-analysis">
              <ErrorBoundary>
                <JobCreator isLoading={isLoading} />
              </ErrorBoundary>
            </TabsContent>

            {/* Recent Jobs Tab */}
            <TabsContent value="recent-jobs">
              <ErrorBoundary>
                <JobHistory
                  jobs={jobs}
                  activeJobId={activeJobId}
                  onSelectJob={(jobId) => setActiveJob(jobId)}
                />
              </ErrorBoundary>
            </TabsContent>

            {/* Scheduled Tab */}
            <TabsContent value="scheduled">
              <div className="space-y-6">
                <ErrorBoundary>
                  <ScheduleCreator
                  competitors={
                    jobStatus && report
                      ? (report.competitors || []).map((c) => ({ url: c.url, name: c.name, focus_areas: [] }))
                      : []
                  }
                  onCreated={() => setScheduleListKey((key) => key + 1)}
                />
                </ErrorBoundary>
                <ErrorBoundary>
                  <ScheduleList key={scheduleListKey} />
                </ErrorBoundary>
              </div>
            </TabsContent>
          </Tabs>
        </div>

        {/* Right Column: Progress Console */}
        <div className="xl:col-span-1">
          <ErrorBoundary>
            <ProgressConsole
              events={events}
              jobStatus={jobStatus}
              isDemoMode={isDemoMode}
              onCancel={cancelActiveJob}
            />
          </ErrorBoundary>
        </div>
      </div>

      {/* Report Section (shown when report is available) */}
      {report && (
        <div className="mt-6">
          <ErrorBoundary>
            <ReportView report={report} jobId={activeJobId || undefined} />
          </ErrorBoundary>
        </div>
      )}
    </div>
  );
}
