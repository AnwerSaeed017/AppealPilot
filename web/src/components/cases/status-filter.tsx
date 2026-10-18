import Link from "next/link";

import type { CaseStatus } from "@/lib/api/types";
import { CASE_STATUSES, STATUS } from "@/lib/labels";
import { cn } from "@/lib/utils";

export function StatusFilter({
  current,
  hrefFor,
}: {
  current: CaseStatus | undefined;
  hrefFor: (status: CaseStatus | undefined) => string;
}) {
  const options: { value: CaseStatus | undefined; label: string }[] = [
    { value: undefined, label: "All" },
    ...CASE_STATUSES.map((status) => ({ value: status, label: STATUS[status].label })),
  ];
  return (
    <nav aria-label="Filter by status" className="flex flex-wrap gap-1.5">
      {options.map((option) => {
        const active = option.value === current;
        return (
          <Link
            key={option.label}
            href={hrefFor(option.value)}
            aria-current={active ? "page" : undefined}
            className={cn(
              "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
              active
                ? "border-foreground bg-foreground text-background"
                : "bg-card text-muted-foreground hover:border-foreground/30 hover:text-foreground",
            )}
          >
            {option.label}
          </Link>
        );
      })}
    </nav>
  );
}
