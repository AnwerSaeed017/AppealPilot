import { ArrowRightIcon, CircleAlertIcon, CircleCheckIcon, LoaderCircleIcon, UserCheckIcon } from "lucide-react";
import Link from "next/link";
import type { ComponentType } from "react";

import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/misc";
import type { CaseStatus } from "@/lib/api/types";
import { formatCount } from "@/lib/format";
import { cn } from "@/lib/utils";

export type QueueCounts = Record<"AWAITING_APPROVAL" | "RUNNING" | "APPROVED" | "FAILED", number>;

const TILES: {
  status: keyof QueueCounts;
  label: string;
  hint: string;
  icon: ComponentType<{ className?: string }>;
  tone: string;
}[] = [
  {
    status: "AWAITING_APPROVAL",
    label: "Needs review",
    hint: "Drafts waiting for your decision",
    icon: UserCheckIcon,
    tone: "text-warning bg-warning-soft",
  },
  { status: "RUNNING", label: "Running", hint: "Being worked on now", icon: LoaderCircleIcon, tone: "text-info bg-info-soft" },
  { status: "APPROVED", label: "Approved", hint: "Ready to send", icon: CircleCheckIcon, tone: "text-success bg-success-soft" },
  { status: "FAILED", label: "Failed", hint: "Stopped on an error; can be retried", icon: CircleAlertIcon, tone: "text-danger bg-danger-soft" },
];

/**
 * The state of the queue at a glance. Each tile filters the list; the review tile also
 * opens the next case waiting for a decision.
 */
export function QueueStats({
  counts,
  current,
  nextReviewId,
}: {
  counts: QueueCounts;
  current: CaseStatus | undefined;
  nextReviewId: string | null;
}) {
  return (
    <section aria-label="Queue" className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {TILES.map((tile) => {
        const Icon = tile.icon;
        const active = current === tile.status;
        const review = tile.status === "AWAITING_APPROVAL";
        return (
          <div
            key={tile.status}
            className={cn(
              "group relative flex flex-col gap-3 rounded-xl border bg-card p-4 shadow-xs transition-all hover:-translate-y-0.5 hover:shadow-md",
              active && "border-primary ring-1 ring-primary",
              review && counts.AWAITING_APPROVAL > 0 && "border-warning/40",
            )}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <Link
                  href={`/cases?status=${tile.status}`}
                  className="text-sm font-medium after:absolute after:inset-0 after:rounded-xl focus-visible:outline-none focus-visible:after:outline-2 focus-visible:after:outline-ring"
                  aria-current={active ? "page" : undefined}
                >
                  {tile.label}
                </Link>
                <p className="hidden text-xs text-muted-foreground sm:block">{tile.hint}</p>
              </div>
              <span className={cn("flex size-9 items-center justify-center rounded-lg", tile.tone)} aria-hidden="true">
                <Icon className={cn("size-4.5", tile.status === "RUNNING" && counts.RUNNING > 0 && "animate-spin")} />
              </span>
            </div>
            <div className="flex flex-wrap items-end justify-between gap-2">
              <p className="text-3xl font-semibold tracking-tight tabular-nums">{formatCount(counts[tile.status])}</p>
              {review && nextReviewId ? (
                <Link
                  href={`/cases/${encodeURIComponent(nextReviewId)}`}
                  className={cn(buttonVariants({ variant: "cta", size: "sm" }), "relative z-10")}
                >
                  Review next <ArrowRightIcon />
                </Link>
              ) : null}
            </div>
          </div>
        );
      })}
    </section>
  );
}

export function QueueStatsSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4" aria-hidden="true">
      {TILES.map((tile) => (
        <div key={tile.status} className="space-y-3 rounded-xl border bg-card p-4">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-8 w-12" />
        </div>
      ))}
    </div>
  );
}
