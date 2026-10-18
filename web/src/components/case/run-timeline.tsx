import { CheckIcon, CircleDashedIcon, LoaderCircleIcon, MinusIcon, XIcon } from "lucide-react";
import type { ReactNode } from "react";

import type { AuditEvent, CaseStatus } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";
import { stepProgress, type StepState } from "@/lib/progress";
import { cn } from "@/lib/utils";

const ICON: Record<StepState, ReactNode> = {
  done: <CheckIcon className="size-3.5" />,
  active: <LoaderCircleIcon className="size-3.5 animate-spin" />,
  failed: <XIcon className="size-3.5" />,
  waiting: <CircleDashedIcon className="size-3.5" />,
  skipped: <MinusIcon className="size-3.5" />,
  pending: null,
};

const RING: Record<StepState, string> = {
  done: "border-success bg-success text-background",
  active: "border-info bg-info-soft text-info",
  failed: "border-danger bg-danger text-background",
  waiting: "border-warning bg-warning-soft text-warning",
  skipped: "border-dashed border-border bg-card text-muted-foreground",
  pending: "border-border bg-card",
};

const STATE_TEXT: Record<StepState, string> = {
  done: "done",
  active: "in progress",
  failed: "stopped here",
  waiting: "waiting for a reviewer",
  skipped: "skipped",
  pending: "not started",
};

export function RunTimeline({ audit, status }: { audit: readonly AuditEvent[]; status: CaseStatus }) {
  const steps = stepProgress(audit, status);
  return (
    <ol className="relative" aria-label="Workflow progress">
      {steps.map((step, index) => (
        <li key={step.id} className="relative flex gap-3 pb-5 last:pb-0">
          {index < steps.length - 1 ? (
            <span
              aria-hidden="true"
              className={cn(
                "absolute top-6 left-[11px] h-[calc(100%-1.25rem)] w-px",
                step.state === "done" ? "bg-success/50" : "bg-border",
              )}
            />
          ) : null}
          <span
            className={cn(
              "relative z-10 flex size-6 shrink-0 items-center justify-center rounded-full border",
              RING[step.state],
            )}
            aria-hidden="true"
          >
            {ICON[step.state]}
          </span>
          <div className="min-w-0 flex-1 pt-0.5">
            <p
              className={cn(
                "text-sm font-medium",
                (step.state === "pending" || step.state === "skipped") && "text-muted-foreground",
              )}
            >
              {step.label}
              {step.runs > 1 ? (
                <span className="ml-1.5 text-xs font-normal text-muted-foreground">×{step.runs}</span>
              ) : null}
              <span className="sr-only">: {STATE_TEXT[step.state]}</span>
            </p>
            <p className="text-xs break-words text-muted-foreground">
              {step.lastSummary ?? (step.state === "skipped" ? "Not needed for this case." : step.description)}
            </p>
            {step.lastAt ? (
              <p className="mt-0.5 text-[11px] text-muted-foreground tabular-nums">
                {formatDateTime(step.lastAt)}
              </p>
            ) : null}
          </div>
        </li>
      ))}
    </ol>
  );
}
