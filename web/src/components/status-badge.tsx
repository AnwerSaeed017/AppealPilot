import { Badge } from "@/components/ui/badge";
import type { CaseStatus, RecommendedAction } from "@/lib/api/types";
import { ACTION, STATUS } from "@/lib/labels";
import { cn } from "@/lib/utils";

const DOT: Record<string, string> = {
  info: "bg-info",
  warning: "bg-warning",
  success: "bg-success",
  danger: "bg-danger",
  neutral: "bg-muted-foreground",
};

export function StatusBadge({ status, className }: { status: CaseStatus; className?: string }) {
  const { label, tone, description } = STATUS[status];
  return (
    <Badge tone={tone} className={className} title={description}>
      <span
        aria-hidden="true"
        className={cn("size-1.5 rounded-full", DOT[tone], status === "RUNNING" && "animate-pulse")}
      />
      {label}
    </Badge>
  );
}

export function ActionBadge({
  action,
  className,
}: {
  action: RecommendedAction | null | undefined;
  className?: string;
}) {
  if (!action) return <span className="text-muted-foreground">—</span>;
  return (
    <Badge tone="outline" className={className} title={ACTION[action].description}>
      {ACTION[action].label}
    </Badge>
  );
}

export function VerifiedBadge({ verified }: { verified: boolean | null | undefined }) {
  if (verified == null) return <span className="text-muted-foreground">—</span>;
  return verified ? (
    <Badge tone="success">Verified</Badge>
  ) : (
    <Badge tone="danger" title="At least one assertion failed verification.">
      Unverified
    </Badge>
  );
}
