"use client";

import { useState } from "react";
import { Clock, Play, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "@/components/ui/toast";
import { createSchedule } from "@/lib/api";
import type { ScheduleFrequency, CompetitorInput } from "@/types";

interface ScheduleCreatorProps {
  competitors: CompetitorInput[];
  query?: string;
  onCreated?: () => void;
}

const FREQUENCY_OPTIONS: { value: ScheduleFrequency; label: string }[] = [
  { value: "hourly", label: "Every Hour" },
  { value: "daily", label: "Daily" },
  { value: "weekly", label: "Weekly" },
  { value: "custom", label: "Custom Cron" },
];

interface CompetitorField {
  url: string;
  name: string;
  focus_areas: string;
}

const EMPTY_COMPETITOR: CompetitorField = { url: "", name: "", focus_areas: "" };

function getNextRunPreview(freq: ScheduleFrequency, cron?: string): string {
  const now = new Date();
  switch (freq) {
    case "hourly":
      return `Next run: ${new Date(now.getTime() + 3600000).toLocaleTimeString()}`;
    case "daily":
      return `Next run: Tomorrow at ${now.toLocaleTimeString()}`;
    case "weekly":
      return `Next run: ${new Date(now.getTime() + 7 * 86400000).toLocaleDateString()}`;
    case "custom":
      return cron ? `Cron: ${cron}` : "Enter a cron expression";
    default:
      return "";
  }
}

export function ScheduleCreator({ competitors, query, onCreated }: ScheduleCreatorProps) {
  const [frequency, setFrequency] = useState<ScheduleFrequency>("daily");
  const [cronExpression, setCronExpression] = useState("");
  const [localCompetitors, setLocalCompetitors] = useState<CompetitorField[]>([
    { ...EMPTY_COMPETITOR },
  ]);
  const [loading, setLoading] = useState(false);

  const usesLocalCompetitors = competitors.length === 0;

  function updateCompetitor(index: number, field: keyof CompetitorField, value: string) {
    setLocalCompetitors((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], [field]: value };
      return next;
    });
  }

  function buildCompetitors(): CompetitorInput[] {
    if (!usesLocalCompetitors) return competitors;
    return localCompetitors
      .filter((c) => c.url.trim())
      .map((c) => ({
        url: c.url.trim(),
        name: c.name.trim() || undefined,
        focus_areas: c.focus_areas
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      }));
  }

  function canCreate(): boolean {
    const selected = buildCompetitors();
    if (selected.length === 0) return false;
    if (frequency === "custom" && !cronExpression.trim()) return false;
    return selected.every((c) => {
      try {
        const url = new URL(c.url);
        return url.protocol === "http:" || url.protocol === "https:";
      } catch {
        return false;
      }
    });
  }

  async function handleCreate() {
    const selectedCompetitors = buildCompetitors();
    if (selectedCompetitors.length === 0) {
      toast({ variant: "error", title: "No Competitors", description: "Add at least one competitor URL." });
      return;
    }

    setLoading(true);
    try {
      await createSchedule({
        competitors: selectedCompetitors,
        query,
        schedule: {
          frequency,
          cron_expression: frequency === "custom" ? cronExpression : undefined,
        },
      });

      toast({
        variant: "success",
        title: "Schedule Created",
        description: `Analysis scheduled to run ${frequency}.`,
      });

      onCreated?.();
    } catch (err) {
      toast({
        variant: "error",
        title: "Schedule Failed",
        description: err instanceof Error ? err.message : "Could not create schedule.",
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Clock className="h-5 w-5 text-accent" />
          Schedule Recurring Analysis
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {usesLocalCompetitors && (
          <div className="space-y-3">
            {localCompetitors.map((comp, i) => (
              <div key={i} className="space-y-2 rounded-lg border border-border p-3">
                <div className="flex items-center justify-between">
                  <Label className="text-xs uppercase tracking-wider text-text-muted">
                    Competitor {i + 1}
                  </Label>
                  {localCompetitors.length > 1 && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => setLocalCompetitors((prev) => prev.filter((_, idx) => idx !== i))}
                      aria-label={`Remove competitor ${i + 1}`}
                    >
                      <Trash2 className="h-3.5 w-3.5 text-error" />
                    </Button>
                  )}
                </div>
                <Input
                  type="url"
                  placeholder="https://example.com"
                  value={comp.url}
                  onChange={(e) => updateCompetitor(i, "url", e.target.value)}
                  aria-label={`Scheduled competitor ${i + 1} URL`}
                />
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                  <Input
                    type="text"
                    placeholder="Name (optional)"
                    value={comp.name}
                    onChange={(e) => updateCompetitor(i, "name", e.target.value)}
                    aria-label={`Scheduled competitor ${i + 1} name`}
                  />
                  <Input
                    type="text"
                    placeholder="Focus areas (comma-sep)"
                    value={comp.focus_areas}
                    onChange={(e) => updateCompetitor(i, "focus_areas", e.target.value)}
                    aria-label={`Scheduled competitor ${i + 1} focus areas`}
                  />
                </div>
              </div>
            ))}
            <button
              type="button"
              onClick={() => setLocalCompetitors((prev) => [...prev, { ...EMPTY_COMPETITOR }])}
              className="w-full rounded-lg border border-dashed border-border py-2 text-sm text-text-secondary transition-colors hover:border-accent hover:text-accent flex items-center justify-center gap-2"
            >
              <Plus className="h-4 w-4" />
              Add Competitor
            </button>
          </div>
        )}

        <div className="space-y-2">
          <Label htmlFor="schedule-frequency">Frequency</Label>
          <Select value={frequency} onValueChange={(v) => setFrequency(v as ScheduleFrequency)}>
            <SelectTrigger id="schedule-frequency" aria-label="Schedule frequency">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {FREQUENCY_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {frequency === "custom" && (
          <div className="space-y-2">
            <Label htmlFor="cron-expression">Cron Expression</Label>
            <Input
              id="cron-expression"
              placeholder="0 9 * * 1-5"
              value={cronExpression}
              onChange={(e) => setCronExpression(e.target.value)}
              aria-describedby="cron-help"
            />
            <p id="cron-help" className="text-xs text-text-muted">
              Format: minute hour day-of-month month day-of-week (e.g., &quot;0 9 * * 1-5&quot; = weekdays at 9am)
            </p>
          </div>
        )}

        <p className="text-sm text-text-secondary">
          {getNextRunPreview(frequency, cronExpression)}
        </p>

        <Button onClick={handleCreate} isLoading={loading} disabled={!canCreate()} className="w-full">
          <Play className="h-4 w-4" />
          Create Schedule
        </Button>
      </CardContent>
    </Card>
  );
}
