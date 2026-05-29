"use client";

import { ThemeToggle } from "@/components/ThemeToggle";

export function Header() {
  return (
    <header className="border-b border-border bg-bg-card">
      <div className="mx-auto max-w-7xl flex items-center justify-between px-4 sm:px-6 py-3">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent text-text-inverse">
            <svg
              className="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
              />
            </svg>
          </div>
          <div>
            <h1 className="text-sm font-semibold text-text-primary">
              Market Intelligence Agent
            </h1>
            <p className="text-xs text-text-muted hidden sm:block">
              Competitive analysis powered by AI
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="hidden sm:inline-flex items-center rounded-full bg-accent-subtle px-2.5 py-1 text-xs font-medium text-accent">
            Powered by Bright Data
          </span>
          <div className="flex items-center gap-1.5">
            <div className="h-1.5 w-1.5 rounded-full bg-success" />
            <span className="text-xs text-text-muted hidden sm:inline">Online</span>
          </div>
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
