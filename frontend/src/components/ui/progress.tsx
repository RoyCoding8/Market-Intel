"use client";

import * as React from "react";
import { cn, formatProgress } from "@/lib/utils";

interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value: number;
  showLabel?: boolean;
  variant?: "default" | "success" | "error";
}

const Progress = React.forwardRef<HTMLDivElement, ProgressProps>(
  ({ className, value, showLabel = false, variant = "default", ...props }, ref) => {
    const percentage = Math.round(Math.max(0, Math.min(100, value * 100)));
    const colorClass =
      variant === "success"
        ? "bg-success"
        : variant === "error"
        ? "bg-error"
        : "bg-accent";

    return (
      <div className={cn("flex items-center gap-3", className)} ref={ref} {...props}>
        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-bg-primary">
          <div
            className={cn("h-full transition-all duration-500 rounded-full", colorClass)}
            style={{ width: `${percentage}%` }}
            role="progressbar"
            aria-valuenow={percentage}
            aria-valuemin={0}
            aria-valuemax={100}
          />
        </div>
        {showLabel && (
          <span className="text-xs font-medium text-text-secondary tabular-nums shrink-0">
            {formatProgress(value)}
          </span>
        )}
      </div>
    );
  }
);
Progress.displayName = "Progress";

export { Progress };
