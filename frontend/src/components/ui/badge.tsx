"use client";

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors",
  {
    variants: {
      variant: {
        default: "bg-bg-secondary border border-border text-text-secondary",
        success:
          "bg-success-subtle text-success border border-success/20",
        warning:
          "bg-warning-subtle text-warning border border-warning/20",
        error: "bg-error-subtle text-error border border-error/20",
        info: "bg-accent-subtle text-accent border border-accent/20",
        outline: "border border-border text-text-primary",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
