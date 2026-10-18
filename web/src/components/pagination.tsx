import { ChevronLeftIcon, ChevronRightIcon } from "lucide-react";
import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { formatCount } from "@/lib/format";
import { cn } from "@/lib/utils";

export function Pagination({
  page,
  pageSize,
  total,
  hrefFor,
}: {
  page: number;
  pageSize: number;
  total: number;
  hrefFor: (page: number) => string;
}) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  const first = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const last = Math.min(total, page * pageSize);
  const linkClass = cn(buttonVariants({ variant: "outline", size: "sm" }));
  const disabledClass = cn(linkClass, "pointer-events-none opacity-50");

  return (
    <nav aria-label="Pagination" className="flex items-center justify-between gap-4 px-1 text-sm">
      <p className="text-muted-foreground">
        {total === 0
          ? "No cases"
          : `${formatCount(first)}–${formatCount(last)} of ${formatCount(total)}`}
      </p>
      <div className="flex items-center gap-2">
        {page > 1 ? (
          <Link className={linkClass} href={hrefFor(page - 1)} rel="prev">
            <ChevronLeftIcon /> Previous
          </Link>
        ) : (
          <span className={disabledClass} aria-disabled="true">
            <ChevronLeftIcon /> Previous
          </span>
        )}
        <span className="text-muted-foreground tabular-nums">
          {page} / {pages}
        </span>
        {page < pages ? (
          <Link className={linkClass} href={hrefFor(page + 1)} rel="next">
            Next <ChevronRightIcon />
          </Link>
        ) : (
          <span className={disabledClass} aria-disabled="true">
            Next <ChevronRightIcon />
          </span>
        )}
      </div>
    </nav>
  );
}
