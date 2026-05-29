"use client";

import { useState } from "react";
import { BarChart3, Search, GitCompare, Lightbulb } from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from "@/components/ui/tabs";
import { FindingCard } from "./FindingCard";
import { ComparisonTable } from "./ComparisonTable";
import { ExportButton } from "./ExportButton";
import type { IntelligenceReport } from "@/types";

interface ReportViewProps {
  report: IntelligenceReport;
  jobId?: string;
}

function StatBadge({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="rounded-lg border border-border bg-bg-secondary px-4 py-3">
      <p className="text-xs font-medium uppercase tracking-wider text-text-muted">
        {label}
      </p>
      <p className="mt-1 text-lg font-bold text-text-primary tabular-nums">
        {value}
      </p>
    </div>
  );
}

export function ReportView({ report, jobId }: ReportViewProps) {
  const [findingFilter, setFindingFilter] = useState<string>("all");

  const categories = Array.from(
    new Set(report.findings.map((f) => f.category))
  );

  const filteredFindings =
    findingFilter === "all"
      ? report.findings
      : report.findings.filter((f) => f.category === findingFilter);

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
            <div>
              <CardTitle className="text-xl">{report.title}</CardTitle>
              <p className="mt-1 text-xs text-text-secondary">
                Generated{" "}
                {new Date(report.created_at).toLocaleDateString("en-US", {
                  year: "numeric",
                  month: "long",
                  day: "numeric",
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </p>
            </div>
            {jobId && <ExportButton jobId={jobId} />}
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatBadge
              label="Competitors"
              value={report.competitors.length}
            />
            <StatBadge label="Findings" value={report.findings.length} />
            <StatBadge label="Sources" value={report.total_sources} />
            <StatBadge
              label="Verification Passes"
              value={report.verification_passes}
            />
          </div>
        </CardContent>
      </Card>

      <Tabs defaultValue="overview">
        <TabsList className="w-full sm:w-auto flex flex-wrap">
          <TabsTrigger value="overview">
            <BarChart3 className="h-4 w-4 mr-1.5 hidden sm:inline" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="findings">
            <Search className="h-4 w-4 mr-1.5 hidden sm:inline" />
            Findings ({report.findings.length})
          </TabsTrigger>
          <TabsTrigger value="comparison">
            <GitCompare className="h-4 w-4 mr-1.5 hidden sm:inline" />
            Comparison ({report.comparison_tables.length})
          </TabsTrigger>
          <TabsTrigger value="recommendations">
            <Lightbulb className="h-4 w-4 mr-1.5 hidden sm:inline" />
            Recommendations ({report.recommendations.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-semibold uppercase tracking-wider text-accent">
                  Executive Summary
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm leading-relaxed text-text-secondary">
                  {report.executive_summary}
                </p>
              </CardContent>
            </Card>

            {report.trend_analysis && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm font-semibold uppercase tracking-wider text-accent">
                    Trend Analysis
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm leading-relaxed text-text-secondary">
                    {report.trend_analysis}
                  </p>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>

        <TabsContent value="findings">
          <div className="space-y-4">
            {categories.length > 1 && (
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => setFindingFilter("all")}
                  className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                    findingFilter === "all"
                      ? "bg-accent text-text-inverse"
                      : "bg-bg-secondary text-text-secondary hover:text-text-primary border border-border"
                  }`}
                >
                  All ({report.findings.length})
                </button>
                {categories.map((cat) => {
                  const count = report.findings.filter(
                    (f) => f.category === cat
                  ).length;
                  return (
                    <button
                      key={cat}
                      onClick={() => setFindingFilter(cat)}
                      className={`rounded-full px-3 py-1 text-xs font-medium capitalize transition-colors ${
                        findingFilter === cat
                          ? "bg-accent text-text-inverse"
                          : "bg-bg-secondary text-text-secondary hover:text-text-primary border border-border"
                      }`}
                    >
                      {cat.replace(/_/g, " ")} ({count})
                    </button>
                  );
                })}
              </div>
            )}

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              {filteredFindings.map((finding, i) => (
                <FindingCard key={finding.id} finding={finding} index={i} />
              ))}
            </div>

            {filteredFindings.length === 0 && (
              <p className="text-sm text-text-muted text-center py-8">
                No findings in this category.
              </p>
            )}
          </div>
        </TabsContent>

        <TabsContent value="comparison">
          {report.comparison_tables.length > 0 ? (
            <div className="space-y-4">
              {report.comparison_tables.map((table, i) => (
                <ComparisonTable
                  key={i}
                  table={table}
                  competitors={report.competitors}
                />
              ))}
            </div>
          ) : (
            <p className="text-sm text-text-muted text-center py-8">
              No comparison tables available.
            </p>
          )}
        </TabsContent>

        <TabsContent value="recommendations">
          {report.recommendations.length > 0 ? (
            <Card>
              <CardContent className="p-6">
                <ol className="space-y-4">
                  {report.recommendations.map((rec, i) => (
                    <li key={i} className="flex items-start gap-3">
                      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent-subtle text-xs font-bold text-accent">
                        {i + 1}
                      </span>
                      <p className="text-sm leading-relaxed text-text-secondary">
                        {rec}
                      </p>
                    </li>
                  ))}
                </ol>
              </CardContent>
            </Card>
          ) : (
            <p className="text-sm text-text-muted text-center py-8">
              No recommendations available.
            </p>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
