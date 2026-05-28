import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/** Merge Tailwind classes with clsx + tailwind-merge. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Format a date string to relative time ("2 hours ago") or absolute format. */
export function formatDate(
  dateStr?: string | null,
  mode: "relative" | "absolute" = "relative"
): string {
  if (!dateStr) return "—";
  try {
    const date = new Date(dateStr);
    if (mode === "absolute") {
      return date.toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    }
    const now = Date.now();
    const diffMs = now - date.getTime();
    const diffSecs = Math.floor(diffMs / 1000);
    if (diffSecs < 60) return "Just now";
    const diffMins = Math.floor(diffSecs / 60);
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 30) return `${diffDays}d ago`;
    const diffMonths = Math.floor(diffDays / 30);
    return `${diffMonths}mo ago`;
  } catch {
    return "—";
  }
}

/** Format progress 0.0–1.0 to percentage string. */
export function formatProgress(progress: number): string {
  return `${Math.round(Math.max(0, Math.min(1, progress)) * 100)}%`;
}

/** Map confidence level to Tailwind color class. */
export function confidenceColor(level: string): {
  bg: string;
  text: string;
  border: string;
} {
  switch (level) {
    case "high":
      return {
        bg: "bg-success/15",
        text: "text-success",
        border: "border-success/30",
      };
    case "medium":
      return {
        bg: "bg-warning/15",
        text: "text-warning",
        border: "border-warning/30",
      };
    case "low":
      return {
        bg: "bg-error/15",
        text: "text-error",
        border: "border-error/30",
      };
    default:
      return {
        bg: "bg-text-muted/15",
        text: "text-text-muted",
        border: "border-text-muted/30",
      };
  }
}

/** Map job status to Tailwind color class. */
export function statusColor(status: string): {
  bg: string;
  text: string;
  dot: string;
  label: string;
} {
  const config: Record<
    string,
    { bg: string; text: string; dot: string; label: string }
  > = {
    pending: {
      bg: "bg-text-muted/15",
      text: "text-text-muted",
      dot: "bg-text-muted",
      label: "Pending",
    },
    scraping: {
      bg: "bg-accent/15",
      text: "text-accent",
      dot: "bg-accent",
      label: "Scraping",
    },
    analyzing: {
      bg: "bg-accent/15",
      text: "text-accent",
      dot: "bg-accent",
      label: "Analyzing",
    },
    verifying: {
      bg: "bg-warning/15",
      text: "text-warning",
      dot: "bg-warning",
      label: "Verifying",
    },
    generating_report: {
      bg: "bg-accent/15",
      text: "text-accent",
      dot: "bg-accent",
      label: "Generating",
    },
    completed: {
      bg: "bg-success/15",
      text: "text-success",
      dot: "bg-success",
      label: "Complete",
    },
    failed: {
      bg: "bg-error/15",
      text: "text-error",
      dot: "bg-error",
      label: "Failed",
    },
    cancelled: {
      bg: "bg-text-muted/15",
      text: "text-text-muted",
      dot: "bg-text-muted",
      label: "Cancelled",
    },
  };
  return config[status] ?? config.pending;
}

/** Format a number with commas (e.g., 1234 -> "1,234"). */
export function formatNumber(n: number): string {
  return n.toLocaleString("en-US");
}
