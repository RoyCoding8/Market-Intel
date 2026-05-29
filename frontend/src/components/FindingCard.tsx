"use client";

import { useState } from "react";
import { ChevronRight, ExternalLink } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { confidenceColor } from "@/lib/utils";
import type { Finding, ConfidenceLevel } from "@/types";

interface FindingCardProps {
  finding: Finding;
  index: number;
}

function ConfidenceBadge({
  level,
  score,
}: {
  level: ConfidenceLevel;
  score: number;
}) {
  const variant =
    level === "high" ? "success" : level === "medium" ? "warning" : "error";
  return (
    <Badge variant={variant}>
      {level.charAt(0).toUpperCase() + level.slice(1)} (
      {Math.round(score * 100)}%)
    </Badge>
  );
}

function safeHttpUrl(value: string): string | undefined {
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:"
      ? value
      : undefined;
  } catch {
    return undefined;
  }
}

const CATEGORY_COLORS: Record<string, string> = {
  pricing: "bg-accent-subtle text-accent",
  features: "bg-success-subtle text-success",
  ecosystem: "bg-warning-subtle text-warning",
  market_positioning: "bg-error-subtle text-error",
  developer_experience: "bg-accent-subtle text-accent",
};

export function FindingCard({ finding, index }: FindingCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const categoryColor =
    CATEGORY_COLORS[finding.category] || "bg-bg-secondary text-text-secondary";

  return (
    <Card hover className="transition-colors">
      <CardContent className="p-5">
        <div className="mb-3 flex items-start justify-between gap-3">
          <div className="flex items-start gap-3 min-w-0">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-accent-subtle font-mono text-xs font-bold text-accent">
              {index + 1}
            </div>
            <div className="min-w-0">
              <h4 className="text-sm font-semibold text-text-primary leading-tight">
                {finding.title}
              </h4>
              <span
                className={`mt-1 inline-block rounded px-1.5 py-0.5 text-xs capitalize ${categoryColor}`}
              >
                {finding.category.replace(/_/g, " ")}
              </span>
            </div>
          </div>
          <ConfidenceBadge
            level={finding.confidence}
            score={finding.confidence_score}
          />
        </div>

        <p className="mb-3 text-sm leading-relaxed text-text-secondary">
          {finding.summary}
        </p>

        {finding.impact && (
          <div className="mb-3 rounded-lg border border-accent/10 bg-accent-subtle p-3">
            <p className="text-xs font-medium uppercase tracking-wider text-accent mb-1">
              Impact
            </p>
            <p className="text-sm text-text-secondary">{finding.impact}</p>
          </div>
        )}

        {finding.recommendation && (
          <div className="mb-3 rounded-lg border border-success/10 bg-success-subtle p-3">
            <p className="text-xs font-medium uppercase tracking-wider text-success mb-1">
              Recommendation
            </p>
            <p className="text-sm text-text-secondary">
              {finding.recommendation}
            </p>
          </div>
        )}

        {finding.citations.length > 0 && (
          <div>
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="flex items-center gap-2 text-xs text-text-secondary hover:text-accent transition-colors"
              aria-expanded={isExpanded}
              aria-label={`${isExpanded ? "Hide" : "Show"} ${finding.citations.length} sources`}
            >
              <ChevronRight
                className={`h-3 w-3 transition-transform ${isExpanded ? "rotate-90" : ""}`}
              />
              {finding.citations.length} source
              {finding.citations.length !== 1 ? "s" : ""}
            </button>

            {isExpanded && (
              <div className="mt-2 space-y-2">
                {finding.citations.map((citation, ci) => (
                  <div
                    key={ci}
                    className="rounded-md border border-border bg-bg-secondary p-3"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <a
                        href={safeHttpUrl(citation.url)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs font-medium text-accent hover:text-accent-hover transition-colors truncate flex items-center gap-1"
                      >
                        {citation.title || citation.url}
                        <ExternalLink className="h-3 w-3 shrink-0" />
                      </a>
                      <ConfidenceBadge level={citation.confidence} score={0.8} />
                    </div>
                    <blockquote className="mt-1 border-l-2 border-accent/30 pl-2 text-xs italic text-text-secondary">
                      &ldquo;{citation.quote}&rdquo;
                    </blockquote>
                    <p className="mt-1 text-xs text-text-muted">
                      Accessed:{" "}
                      {new Date(citation.accessed_at).toLocaleDateString()}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
