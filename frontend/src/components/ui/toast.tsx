"use client";

import * as React from "react";
import * as ToastPrimitive from "@radix-ui/react-toast";
import { X, CheckCircle, AlertCircle, Info } from "lucide-react";
import { cn } from "@/lib/utils";

const ToastProvider = ToastPrimitive.Provider;

const ToastViewport = React.forwardRef<
  React.ElementRef<typeof ToastPrimitive.Viewport>,
  React.ComponentPropsWithoutRef<typeof ToastPrimitive.Viewport>
>(({ className, ...props }, ref) => (
  <ToastPrimitive.Viewport
    ref={ref}
    className={cn(
      "fixed top-0 z-[100] flex max-h-screen w-full flex-col-reverse p-4 sm:bottom-0 sm:right-0 sm:top-auto sm:flex-col md:max-w-[420px]",
      className
    )}
    {...props}
  />
));
ToastViewport.displayName = ToastPrimitive.Viewport.displayName;

type ToastVariant = "success" | "error" | "info";

interface ToastData {
  id: string;
  variant: ToastVariant;
  title: string;
  description?: string;
}

const toastListeners: Array<(toasts: ToastData[]) => void> = [];
let toastList: ToastData[] = [];
const toastTimers = new Map<string, ReturnType<typeof setTimeout>>();

function notifyToast(toast: Omit<ToastData, "id">) {
  const id = Math.random().toString(36).slice(2);
  const newToast = { ...toast, id };
  toastList = [...toastList, newToast];
  toastListeners.forEach((l) => l(toastList));
  const timer = setTimeout(() => {
    dismissToast(id);
  }, 5000);
  toastTimers.set(id, timer);
  return id;
}

function dismissToast(id: string) {
  const timer = toastTimers.get(id);
  if (timer) {
    clearTimeout(timer);
    toastTimers.delete(id);
  }
  toastList = toastList.filter((t) => t.id !== id);
  toastListeners.forEach((l) => l(toastList));
}

function useToastState() {
  const [toasts, setToasts] = React.useState<ToastData[]>(toastList);
  React.useEffect(() => {
    toastListeners.push(setToasts);
    return () => {
      const idx = toastListeners.indexOf(setToasts);
      if (idx > -1) toastListeners.splice(idx, 1);
    };
  }, []);
  return toasts;
}

function ToastIcon({ variant }: { variant: ToastVariant }) {
  switch (variant) {
    case "success":
      return <CheckCircle className="h-4 w-4 text-success shrink-0" />;
    case "error":
      return <AlertCircle className="h-4 w-4 text-error shrink-0" />;
    case "info":
      return <Info className="h-4 w-4 text-accent shrink-0" />;
  }
}

const variantStyles: Record<ToastVariant, string> = {
  success: "border-success/30",
  error: "border-error/30",
  info: "border-accent/30",
};

function ToastNotification({
  toast,
  onDismiss,
}: {
  toast: ToastData;
  onDismiss: () => void;
}) {
  return (
    <ToastPrimitive.Root
      className={cn(
        "group pointer-events-auto relative flex w-full items-start gap-3 overflow-hidden rounded-lg border bg-bg-card p-4 shadow-lg transition-all",
        variantStyles[toast.variant]
      )}
      open
      onOpenChange={(open) => {
        if (!open) onDismiss();
      }}
    >
      <ToastIcon variant={toast.variant} />
      <div className="flex-1 min-w-0">
        <ToastPrimitive.Title className="text-sm font-medium text-text-primary">
          {toast.title}
        </ToastPrimitive.Title>
        {toast.description && (
          <ToastPrimitive.Description className="mt-1 text-xs text-text-secondary">
            {toast.description}
          </ToastPrimitive.Description>
        )}
      </div>
      <ToastPrimitive.Close className="shrink-0 rounded-md p-1 text-text-muted transition-colors hover:text-text-primary">
        <X className="h-3.5 w-3.5" />
        <span className="sr-only">Dismiss</span>
      </ToastPrimitive.Close>
    </ToastPrimitive.Root>
  );
}

function Toaster() {
  const toasts = useToastState();

  return (
    <ToastProvider swipeDirection="right">
      {toasts.map((toast) => (
        <ToastNotification
          key={toast.id}
          toast={toast}
          onDismiss={() => dismissToast(toast.id)}
        />
      ))}
      <ToastViewport />
    </ToastProvider>
  );
}

export {
  Toaster,
  notifyToast as toast,
  dismissToast,
  ToastProvider,
  ToastViewport,
  type ToastData,
  type ToastVariant,
};
