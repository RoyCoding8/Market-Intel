"use client";

import { useEffect, useState } from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
} from "recharts";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getStats } from "@/lib/api";

const CATEGORY_COLORS: Record<string, string> = {
  pricing: "#6366f1",
  features: "#10b981",
  ecosystem: "#f59e0b",
  market_positioning: "#ef4444",
  developer_experience: "#8b5cf6",
  team: "#06b6d4",
  news: "#ec4899",
};

const DEFAULT_COLOR = "#64748b";

const DEMO_CATEGORIES = [
  { name: "Pricing", count: 12, fill: CATEGORY_COLORS.pricing },
  { name: "Features", count: 9, fill: CATEGORY_COLORS.features },
  { name: "Ecosystem", count: 8, fill: CATEGORY_COLORS.ecosystem },
  { name: "Market", count: 7, fill: CATEGORY_COLORS.market_positioning },
  { name: "Dev Exp", count: 6, fill: CATEGORY_COLORS.developer_experience },
  { name: "Team", count: 3, fill: CATEGORY_COLORS.team },
  { name: "News", count: 2, fill: CATEGORY_COLORS.news },
];

function CustomTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ value: number; payload: { name: string } }>;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-border bg-bg-secondary p-3 shadow-xl">
      <p className="text-xs text-text-secondary">{payload[0].payload.name}</p>
      <p className="text-sm font-semibold text-text-primary">
        {payload[0].value} findings
      </p>
    </div>
  );
}

export function CategoryBreakdown() {
  const [data, setData] = useState(DEMO_CATEGORIES);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    getStats()
      .then((stats) => {
        if (cancelled) return;
        if (stats.findings_by_category && Object.keys(stats.findings_by_category).length > 0) {
          const chartData = Object.entries(stats.findings_by_category).map(
            ([key, count]) => ({
              name: key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, " "),
              count,
              fill: CATEGORY_COLORS[key] || DEFAULT_COLOR,
            })
          );
          setData(chartData);
        }
      })
      .catch(() => {
        // keep demo data
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <Card className="p-6">
        <Skeleton className="h-5 w-48 mb-4" />
        <Skeleton className="h-[260px] w-full" />
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Findings by Category</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[260px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={data}
              layout="vertical"
              margin={{ top: 5, right: 20, left: 10, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
              <XAxis
                type="number"
                stroke="#64748b"
                fontSize={11}
                tickLine={false}
                axisLine={{ stroke: "#1e293b" }}
                allowDecimals={false}
              />
              <YAxis
                type="category"
                dataKey="name"
                stroke="#64748b"
                fontSize={11}
                tickLine={false}
                axisLine={{ stroke: "#1e293b" }}
                width={80}
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="count" radius={[0, 4, 4, 0]} barSize={18}>
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
