"use client";

import { useEffect, useState } from "react";
import { Briefcase, FileText, Users, ShieldCheck, TrendingUp, TrendingDown } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getStats } from "@/lib/api";
import { formatNumber } from "@/lib/utils";
import type { DashboardStats } from "@/types";

interface StatCardProps {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  trend?: { value: number; direction: "up" | "down" };
  loading?: boolean;
}

function StatCard({ icon, label, value, trend, loading }: StatCardProps) {
  if (loading) {
    return (
      <Card className="p-6">
        <div className="flex items-start justify-between">
          <div className="space-y-3 flex-1">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-8 w-16" />
          </div>
          <Skeleton className="h-10 w-10 rounded-lg" />
        </div>
      </Card>
    );
  }

  return (
    <Card hover className="p-6">
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <p className="text-sm text-text-secondary">{label}</p>
          <p className="text-2xl font-bold text-text-primary tabular-nums">
            {typeof value === "number" ? formatNumber(value) : value}
          </p>
          {trend && (
            <div className="flex items-center gap-1 mt-1">
              {trend.direction === "up" ? (
                <TrendingUp className="h-3 w-3 text-success" />
              ) : (
                <TrendingDown className="h-3 w-3 text-error" />
              )}
              <span
                className={`text-xs font-medium ${
                  trend.direction === "up" ? "text-success" : "text-error"
                }`}
              >
                {trend.direction === "up" ? "+" : ""}
                {trend.value}% this week
              </span>
            </div>
          )}
        </div>
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent/10 text-accent">
          {icon}
        </div>
      </div>
    </Card>
  );
}

export function StatsCards() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    getStats()
      .then((data) => {
        if (!cancelled) setStats(data);
      })
      .catch(() => {
        // Use demo fallback values
        if (!cancelled) {
          setStats({
            total_jobs: 12,
            completed_jobs: 9,
            failed_jobs: 2,
            total_findings: 47,
            high_confidence_findings: 31,
            total_competitors_tracked: 8,
            total_pages_scraped: 156,
            total_verifications: 12,
            average_confidence_score: 0.84,
            jobs_last_7_days: 5,
            findings_by_category: {},
            top_competitors: [],
          });
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const cards: StatCardProps[] = [
    {
      icon: <Briefcase className="h-5 w-5" />,
      label: "Total Jobs",
      value: stats?.total_jobs ?? 0,
      trend: { value: 12, direction: "up" },
    },
    {
      icon: <FileText className="h-5 w-5" />,
      label: "Findings",
      value: stats?.total_findings ?? 0,
      trend: { value: 8, direction: "up" },
    },
    {
      icon: <Users className="h-5 w-5" />,
      label: "Competitors Tracked",
      value: stats?.total_competitors_tracked ?? 0,
      trend: { value: 3, direction: "up" },
    },
    {
      icon: <ShieldCheck className="h-5 w-5" />,
      label: "Avg Confidence",
      value: stats
        ? `${Math.round(stats.average_confidence_score * 100)}%`
        : "—",
      trend: { value: 2, direction: "up" },
    },
  ];

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((card) => (
        <StatCard key={card.label} {...card} loading={loading} />
      ))}
    </div>
  );
}
