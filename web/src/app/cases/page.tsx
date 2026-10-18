import { PlusIcon } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { CaseTable, CaseTableSkeleton } from "@/components/cases/case-table";
import { QueueStats, QueueStatsSkeleton, type QueueCounts } from "@/components/cases/queue-stats";
import { StatusFilter } from "@/components/cases/status-filter";
import { PageHeader } from "@/components/page-header";
import { Pagination } from "@/components/pagination";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { listCases } from "@/lib/api/client";
import type { CaseStatus } from "@/lib/api/types";
import { CASE_STATUSES } from "@/lib/labels";

export const metadata: Metadata = { title: "Cases" };

const PAGE_SIZE = 20;

type Query = { status?: CaseStatus; page: number };

function readQuery(params: Record<string, string | string[] | undefined>): Query {
  const status = typeof params.status === "string" ? params.status : undefined;
  const page = Number(typeof params.page === "string" ? params.page : "1");
  return {
    status: CASE_STATUSES.includes(status as CaseStatus) ? (status as CaseStatus) : undefined,
    page: Number.isInteger(page) && page > 0 ? page : 1,
  };
}

function hrefFor(query: Query): string {
  const search = new URLSearchParams();
  if (query.status) search.set("status", query.status);
  if (query.page > 1) search.set("page", String(query.page));
  const text = search.toString();
  return text ? `/cases?${text}` : "/cases";
}

export default function CasesPage({ searchParams }: PageProps<"/cases">) {
  return (
    <>
      <PageHeader
        title="Cases"
        description="Denied claims and where each one stands. A case waits for a reviewer before anything leaves the practice."
        actions={
          <Button asChild variant="cta">
            <Link href="/cases/new">
              <PlusIcon /> New case
            </Link>
          </Button>
        }
      />
      <div className="space-y-6">
        <Suspense fallback={<QueueStatsSkeleton />}>
          <Queue searchParams={searchParams} />
        </Suspense>
        <Suspense fallback={<CaseTableSkeleton />}>
          <CaseResults searchParams={searchParams} />
        </Suspense>
      </div>
    </>
  );
}

async function Queue({ searchParams }: { searchParams: PageProps<"/cases">["searchParams"] }) {
  const query = readQuery(await searchParams);
  // One small request per status: the API's total gives the count, and the first case
  // waiting for review is the one "Review next" opens.
  const [review, running, approved, failed] = await Promise.all(
    (["AWAITING_APPROVAL", "RUNNING", "APPROVED", "FAILED"] as const).map((status) => listCases(1, 1, status)),
  );
  const counts: QueueCounts = {
    AWAITING_APPROVAL: review.total,
    RUNNING: running.total,
    APPROVED: approved.total,
    FAILED: failed.total,
  };
  return <QueueStats counts={counts} current={query.status} nextReviewId={review.items[0]?.case_id ?? null} />;
}

async function CaseResults({ searchParams }: { searchParams: PageProps<"/cases">["searchParams"] }) {
  const query = readQuery(await searchParams);
  const result = await listCases(query.page, PAGE_SIZE, query.status);
  return (
    <div className="space-y-4">
      <StatusFilter
        current={query.status}
        hrefFor={(status) => hrefFor({ status, page: 1 })}
      />
      <Card className="overflow-hidden">
        <CaseTable cases={result.items} filtered={query.status !== undefined} />
      </Card>
      <Pagination
        page={result.page}
        pageSize={result.page_size}
        total={result.total}
        hrefFor={(page) => hrefFor({ ...query, page })}
      />
    </div>
  );
}
