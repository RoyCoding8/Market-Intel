"use client";

import { useState } from "react";
import { Download, FileJson, FileSpreadsheet, FileText, FileIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "@/components/ui/toast";
import { exportReport } from "@/lib/api";
import type { ExportFormat } from "@/types";

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

interface ExportButtonProps {
  jobId: string;
  variant?: "primary" | "secondary" | "ghost" | "outline";
  size?: "sm" | "md" | "lg";
}

const FORMAT_OPTIONS: { value: ExportFormat; label: string; icon: React.ReactNode }[] = [
  { value: "json", label: "JSON", icon: <FileJson className="h-4 w-4" /> },
  { value: "csv", label: "CSV", icon: <FileSpreadsheet className="h-4 w-4" /> },
  { value: "markdown", label: "Markdown", icon: <FileText className="h-4 w-4" /> },
  { value: "pdf", label: "PDF", icon: <FileIcon className="h-4 w-4" /> },
];

export function ExportButton({
  jobId,
  variant = "outline",
  size = "sm",
}: ExportButtonProps) {
  const [format, setFormat] = useState<ExportFormat>("json");
  const [loading, setLoading] = useState(false);

  async function handleExport() {
    setLoading(true);
    try {
      const res = await exportReport(jobId, {
        format,
        include_citations: true,
        include_raw_data: false,
      });

      // Trigger download
      if (res.content) {
        const mimeTypes: Record<string, string> = {
          json: "application/json",
          csv: "text/csv",
          markdown: "text/markdown",
          pdf: "application/pdf",
        };
        const blob = new Blob([res.content], {
          type: mimeTypes[format] || "text/plain",
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `report-${jobId}.${format === "markdown" ? "md" : format}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      } else if (res.download_url) {
        // Validate: only open relative paths to prevent open redirect
        const url = res.download_url;
        if (url.startsWith("/") && !url.startsWith("//")) {
          window.open(`${API_BASE}${url}`, "_blank", "noopener,noreferrer");
        } else {
          toast({ variant: "error", title: "Invalid download URL", description: "Download URL must be a relative path." });
        }
      }

      toast({
        variant: "success",
        title: "Export Ready",
        description: `Report exported as ${format.toUpperCase()}.`,
      });
    } catch (err) {
      toast({
        variant: "error",
        title: "Export Failed",
        description: err instanceof Error ? err.message : "Could not export report.",
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex items-center gap-2">
      <Select value={format} onValueChange={(v) => setFormat(v as ExportFormat)}>
        <SelectTrigger className="w-[130px] h-9" aria-label="Export format">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {FORMAT_OPTIONS.map((opt) => (
            <SelectItem key={opt.value} value={opt.value}>
              <span className="flex items-center gap-2">
                {opt.icon}
                {opt.label}
              </span>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Button
        variant={variant}
        size={size}
        onClick={handleExport}
        isLoading={loading}
        aria-label={`Export report as ${format}`}
      >
        <Download className="h-4 w-4" />
        Export
      </Button>
    </div>
  );
}
