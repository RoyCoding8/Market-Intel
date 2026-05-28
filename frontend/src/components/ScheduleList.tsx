"use client";

import { useEffect, useState, useCallback } from "react";
import { Clock, Trash2, ToggleLeft, ToggleRight, RefreshCw } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog";
import { toast } from "@/components/ui/toast";
import { listSchedules, updateSchedule, deleteSchedule } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import type { ScheduledJobResponse } from "@/types";

export function ScheduleList() {
  const [schedules, setSchedules] = useState<ScheduledJobResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleteTarget, setDeleteTarget] = useState<ScheduledJobResponse | null>(null);
  const [deleting, setDeleting] = useState(false);

  const fetchSchedules = useCallback(async () => {
    try {
      const res = await listSchedules();
      setSchedules(res.schedules);
    } catch {
      // Backend may not be available
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSchedules();
  }, [fetchSchedules]);

  async function handleToggle(schedule: ScheduledJobResponse) {
    try {
      await updateSchedule(schedule.schedule_id, { enabled: !schedule.enabled });
      setSchedules((prev) =>
        prev.map((s) =>
          s.schedule_id === schedule.schedule_id ? { ...s, enabled: !s.enabled } : s
        )
      );
      toast({
        variant: "success",
        title: schedule.enabled ? "Schedule Disabled" : "Schedule Enabled",
        description: `The ${schedule.frequency} schedule has been ${schedule.enabled ? "disabled" : "enabled"}.`,
      });
    } catch (err) {
      toast({
        variant: "error",
        title: "Update Failed",
        description: err instanceof Error ? err.message : "Could not update schedule.",
      });
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await deleteSchedule(deleteTarget.schedule_id);
      setSchedules((prev) => prev.filter((s) => s.schedule_id !== deleteTarget.schedule_id));
      toast({ variant: "success", title: "Schedule Deleted" });
      setDeleteTarget(null);
    } catch (err) {
      toast({
        variant: "error",
        title: "Delete Failed",
        description: err instanceof Error ? err.message : "Could not delete schedule.",
      });
    } finally {
      setDeleting(false);
    }
  }

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5 text-accent" />
            Scheduled Analyses
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-16 w-full rounded-lg" />
          ))}
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5 text-accent" />
              Scheduled Analyses
            </CardTitle>
            <Button variant="ghost" size="sm" onClick={fetchSchedules} aria-label="Refresh schedules">
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {schedules.length === 0 ? (
            <p className="text-sm text-text-muted text-center py-8">
              No scheduled analyses yet. Create one above.
            </p>
          ) : (
            <div className="space-y-3">
              {schedules.map((schedule) => (
                <div
                  key={schedule.schedule_id}
                  className="flex items-center justify-between gap-4 rounded-lg border border-border bg-bg-primary p-4 transition-colors hover:border-border-hover"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-medium text-text-primary truncate">
                        {schedule.job_config.competitors
                          .map((c) => {
                            if (c.name) return c.name;
                            try { return new URL(c.url).hostname; } catch { return c.url; }
                          })
                          .join(" vs ")}
                      </span>
                      <Badge variant={schedule.enabled ? "success" : "default"}>
                        {schedule.enabled ? "Active" : "Paused"}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-text-secondary">
                      <span className="capitalize">{schedule.frequency}</span>
                      {schedule.cron_expression && (
                        <code className="bg-bg-card px-1.5 py-0.5 rounded text-text-muted font-mono">
                          {schedule.cron_expression}
                        </code>
                      )}
                      {schedule.next_run && (
                        <span>Next: {formatDate(schedule.next_run)}</span>
                      )}
                      {schedule.last_run && (
                        <span>Last: {formatDate(schedule.last_run)}</span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleToggle(schedule)}
                      aria-label={schedule.enabled ? "Disable schedule" : "Enable schedule"}
                    >
                      {schedule.enabled ? (
                        <ToggleRight className="h-5 w-5 text-success" />
                      ) : (
                        <ToggleLeft className="h-5 w-5 text-text-muted" />
                      )}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setDeleteTarget(schedule)}
                      aria-label="Delete schedule"
                    >
                      <Trash2 className="h-4 w-4 text-error" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Schedule</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this scheduled analysis? This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="secondary">Cancel</Button>
            </DialogClose>
            <Button variant="danger" onClick={handleDelete} isLoading={deleting}>
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
