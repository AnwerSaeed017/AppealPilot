import { InboxIcon } from "lucide-react";
import Link from "next/link";

import { ActionBadge, StatusBadge, VerifiedBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/misc";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { CaseSummary } from "@/lib/api/types";
import { formatDate, formatDateTime } from "@/lib/format";
import { payerName } from "@/lib/labels";

export function CaseTable({ cases, filtered }: { cases: CaseSummary[]; filtered: boolean }) {
  if (cases.length === 0) {
    return (
      <div className="flex flex-col items-center gap-3 px-6 py-16 text-center">
        <InboxIcon className="size-8 text-muted-foreground" aria-hidden="true" />
        <div className="space-y-1">
          <p className="font-medium">{filtered ? "No cases with this status" : "No cases yet"}</p>
          <p className="text-sm text-muted-foreground">
            {filtered
              ? "Choose another status, or show all cases."
              : "Start with one of the Medicare sample cases."}
          </p>
        </div>
        {filtered ? null : (
          <Button asChild size="sm">
            <Link href="/cases/new">New case</Link>
          </Button>
        )}
      </div>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow className="hover:bg-transparent">
          <TableHead>Claim</TableHead>
          <TableHead>Payer</TableHead>
          <TableHead>Denial</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Recommended action</TableHead>
          <TableHead>Draft</TableHead>
          <TableHead className="text-right">Updated</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {cases.map((item) => (
          <TableRow key={item.case_id} className="relative">
            <TableCell>
              <Link
                href={`/cases/${encodeURIComponent(item.case_id)}`}
                className="font-medium after:absolute after:inset-0 focus-visible:outline-none focus-visible:after:outline-2 focus-visible:after:outline-ring"
              >
                {item.claim_id}
              </Link>
              <div className="text-xs text-muted-foreground">Worked {formatDate(item.as_of)}</div>
            </TableCell>
            <TableCell>{payerName(item.payer_id)}</TableCell>
            <TableCell className="font-mono text-xs">CARC {item.carc_code}</TableCell>
            <TableCell>
              <StatusBadge status={item.status} />
            </TableCell>
            <TableCell>
              <ActionBadge action={item.action} />
            </TableCell>
            <TableCell>
              <VerifiedBadge verified={item.verified} />
            </TableCell>
            <TableCell className="text-right text-xs whitespace-nowrap text-muted-foreground tabular-nums">
              {formatDateTime(item.updated_at)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

export function CaseTableSkeleton() {
  return (
    <div className="space-y-4" aria-busy="true" aria-label="Loading cases">
      <div className="flex gap-1.5">
        {Array.from({ length: 6 }, (_, index) => (
          <Skeleton key={index} className="h-6 w-20 rounded-full" />
        ))}
      </div>
      <div className="space-y-px overflow-hidden rounded-xl border bg-card">
        {Array.from({ length: 6 }, (_, index) => (
          <div key={index} className="flex items-center gap-4 px-3 py-3.5">
            <Skeleton className="h-4 w-40" />
            <Skeleton className="h-4 w-16" />
            <Skeleton className="h-4 w-16" />
            <Skeleton className="h-5 w-24 rounded-full" />
            <Skeleton className="ml-auto h-4 w-32" />
          </div>
        ))}
      </div>
    </div>
  );
}
