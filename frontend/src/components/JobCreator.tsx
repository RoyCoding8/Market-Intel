"use client";

import { useState } from "react";
import { Plus, Trash2, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useJobStore } from "@/stores/jobStore";
import type { CompetitorInput } from "@/types";

interface CompetitorField {
  url: string;
  name: string;
  focus_areas: string;
}

const EMPTY_COMPETITOR: CompetitorField = { url: "", name: "", focus_areas: "" };

export function JobCreator({ isLoading }: { isLoading: boolean }) {
  const createJob = useJobStore((s) => s.createJob);
  const [competitors, setCompetitors] = useState<CompetitorField[]>([
    { ...EMPTY_COMPETITOR },
    { ...EMPTY_COMPETITOR },
  ]);
  const [query, setQuery] = useState("");

  function updateCompetitor(
    index: number,
    field: keyof CompetitorField,
    value: string
  ) {
    setCompetitors((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], [field]: value };
      return next;
    });
  }

  function addCompetitor() {
    setCompetitors((prev) => [...prev, { ...EMPTY_COMPETITOR }]);
  }

  function removeCompetitor(index: number) {
    if (competitors.length <= 1) return;
    setCompetitors((prev) => prev.filter((_, i) => i !== index));
  }

  function validate(): boolean {
    const filled = competitors.filter((c) => c.url.trim());
    if (filled.length === 0) return false;
    return filled.every((c) => {
      try {
        const url = new URL(c.url.trim());
        return url.protocol === "http:" || url.protocol === "https:";
      } catch {
        return false;
      }
    });
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    const payload: { competitors: CompetitorInput[]; query?: string } = {
      competitors: competitors
        .filter((c) => c.url.trim())
        .map((c) => ({
          url: c.url.trim(),
          name: c.name.trim() || undefined,
          focus_areas: c.focus_areas
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean),
        })),
    };

    if (query.trim()) {
      payload.query = query.trim();
    }

    try {
      await createJob(payload);
    } catch {
      // Error handled in store
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2 mb-1">
          <Sparkles className="h-5 w-5 text-accent" />
          <CardTitle>New Analysis Job</CardTitle>
        </div>
        <p className="text-sm text-text-secondary">
          Enter competitor URLs to analyze pricing, features, team, and news.
          The AI agents will scrape, analyze, verify, and generate an
          intelligence report.
        </p>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          {competitors.map((comp, i) => (
            <div
              key={i}
              className="space-y-3 rounded-lg border border-border p-4"
            >
              <div className="flex items-center justify-between">
                <Label className="text-xs uppercase tracking-wider text-text-muted">
                  Competitor {i + 1}
                </Label>
                {competitors.length > 2 && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => removeCompetitor(i)}
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
                required
                aria-label={`Competitor ${i + 1} URL`}
              />

              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                <Input
                  type="text"
                  placeholder="Name (optional)"
                  value={comp.name}
                  onChange={(e) =>
                    updateCompetitor(i, "name", e.target.value)
                  }
                  aria-label={`Competitor ${i + 1} name`}
                />
                <Input
                  type="text"
                  placeholder="Focus areas (comma-sep)"
                  value={comp.focus_areas}
                  onChange={(e) =>
                    updateCompetitor(i, "focus_areas", e.target.value)
                  }
                  aria-label={`Competitor ${i + 1} focus areas`}
                />
              </div>
            </div>
          ))}

          <button
            type="button"
            onClick={addCompetitor}
            className="w-full rounded-lg border border-dashed border-border py-2.5 text-sm text-text-secondary transition-colors hover:border-accent hover:text-accent flex items-center justify-center gap-2"
          >
            <Plus className="h-4 w-4" />
            Add Competitor
          </button>

          <div className="space-y-2">
            <Label htmlFor="analysis-query">Analysis Query (optional)</Label>
            <Textarea
              id="analysis-query"
              placeholder="e.g., Compare pricing strategies and feature sets..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              rows={2}
            />
          </div>

          <Button
            type="submit"
            className="w-full"
            size="lg"
            isLoading={isLoading}
            disabled={!validate()}
          >
            <Sparkles className="h-4 w-4" />
            Start Intelligence Analysis
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
