import { ArrowLeftIcon, CircleAlertIcon, CircleCheckIcon, CircleXIcon, LoaderCircleIcon } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { AuditView } from "@/components/case/audit-view";
import { ClaimView } from "@/components/case/claim-view";
import { DecisionPanel } from "@/components/case/decision-panel";
import { DraftView } from "@/components/case/draft-view";
import { EvidenceView } from "@/components/case/evidence-view";
import { FindingsView } from "@/components/case/findings-view";
import { LiveUpdates } from "@/components/case/live-updates";
import { RecommendationCard } from "@/components/case/recommendation-card";
import { RetryButton } from "@/components/case/retry-button";
import { RunTimeline } from "@/components/case/run-timeline";
import { PageHeader } from "@/components/page-header";
import { ActionBadge, StatusBadge } from "@/components/status-badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/misc";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { getCase } from "@/lib/api/client";
import type { CaseState, CaseSummary } from "@/lib/api/types";
import { formatCount, formatDate, formatDuration, formatMoney, formatPercent } from "@/lib/format";
import { DECISION, payerName } from "@/lib/labels";
import { stepProgress } from "@/lib/progress";
import { usageOf } from "@/lib/usage";

export const metadata: Metadata = { title: "Case" };

export default function CasePage({ params }: PageProps<"/cases/[id]">) {
  return (
    <>
      <Link
        href="/cases"
        className="mb-4 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeftIcon className="size-4" aria-hidden="true" /> All cases
      </Link>
      <Suspense fallback={<CaseSkeleton />}>
        <CaseDetail params={params} />
      </Suspense>
    </>
  );
}

async function CaseDetail({ params }: { params: PageProps<"/cases/[id]">["params"] }) {
  const { id } = await params;
  const view = await getCase(id);
  if (view === null) notFound();
  const { summary, state } = view;

  return (
    <>
      <CaseHeader summary={summary} state={state ?? null} />
      {state ? <CaseBody summary={summary} state={state} /> : <NoState summary={summary} />}
    </>
  );
}

function CaseHeader({ summary, state }: { summary: CaseSummary; state: CaseState | null }) {
  const denial = state?.case_input.denial;
  return (
    <PageHeader
      title={
        <span className="flex flex-wrap items-center gap-3">
          Claim {summary.claim_id}
          <StatusBadge status={summary.status} />
        </span>
      }
      description={
        denial ? (
          <>
            {payerName(summary.payer_id)} denied {formatMoney(denial.denied_amount)} on {formatDate(denial.denial_date)} with{" "}
            <span className="font-mono">
              {denial.group_code}-{denial.carc_code}
              {(denial.rarc_codes ?? []).length > 0 ? ` ${(denial.rarc_codes ?? []).join(" ")}` : ""}
            </span>
            . Deadlines are judged as of {formatDate(summary.as_of)}.
          </>
        ) : (
          `${payerName(summary.payer_id)} · CARC ${summary.carc_code}`
        )
      }
      actions={summary.status === "RUNNING" ? <LiveUpdates caseId={summary.case_id} /> : null}
    />
  );
}

/**
 * A case whose workflow state has not been saved. While it runs, that is just the first
 * moment of the run. Otherwise the state will never come, and the page says so rather
 * than wait forever.
 */
function NoState({ summary }: { summary: CaseSummary }) {
  if (summary.status === "RUNNING") {
    return (
      <Card>
        <CardContent className="flex items-center gap-3 py-10 text-sm text-muted-foreground">
          <LoaderCircleIcon className="size-4 animate-spin" aria-hidden="true" />
          Starting the workflow…
        </CardContent>
      </Card>
    );
  }
  return (
    <Alert tone={summary.status === "FAILED" ? "danger" : "warning"}>
      <CircleAlertIcon />
      <AlertTitle>No workflow record for this case</AlertTitle>
      <AlertDescription>
        {summary.status === "FAILED"
          ? "The run stopped before its first step was saved, so there is nothing to continue from. Start the case again from New case."
          : "The case is listed, but no step of the workflow was ever saved for it, so there is no draft to review. It was probably created outside the workflow, for example as test data."}
      </AlertDescription>
    </Alert>
  );
}

function Outcome({ summary, state }: { summary: CaseSummary; state: CaseState }) {
  const decision = state.human_decision;
  if (summary.status === "AWAITING_APPROVAL" && state.draft) {
    const unverified = (state.verification?.verdicts ?? []).filter((verdict) => !verdict.supported).length;
    return <DecisionPanel caseId={summary.case_id} summary={state.draft.summary} unverifiedCount={unverified} />;
  }
  if (summary.status === "APPROVED" && decision) {
    return (
      <Alert tone="success">
        <CircleCheckIcon />
        <AlertTitle>{DECISION[decision.kind]}</AlertTitle>
        <AlertDescription>
          {decision.edited_summary ? (
            <p className="whitespace-pre-wrap text-foreground">{decision.edited_summary}</p>
          ) : (
            "The reviewer approved the draft below as written."
          )}
        </AlertDescription>
      </Alert>
    );
  }
  if (summary.status === "REJECTED" && decision) {
    return (
      <Alert tone="neutral">
        <CircleXIcon />
        <AlertTitle>Rejected by the reviewer</AlertTitle>
        <AlertDescription>{decision.reason}</AlertDescription>
      </Alert>
    );
  }
  if (summary.status === "RUNNING") {
    const current = stepProgress(state.audit, summary.status).find((step) => step.state === "active");
    return (
      <Alert tone="info" aria-live="polite">
        <LoaderCircleIcon className="animate-spin" />
        <AlertTitle>{current ? `Working: ${current.label}` : "Working on this case"}</AlertTitle>
        <AlertDescription>
          {current ? `${current.description} ` : ""}This page updates by itself as each step finishes; the
          draft appears below when it has been written and checked.
        </AlertDescription>
      </Alert>
    );
  }
  if (summary.status === "FAILED") {
    return (
      <Alert tone="danger">
        <CircleAlertIcon />
        <AlertTitle>The run stopped on an error</AlertTitle>
        <AlertDescription className="space-y-3">
          <p>
            Every completed step is saved. Retrying continues from the step that did not finish, for example
            after a model provider&apos;s rate limit has reset.
          </p>
          <RetryButton caseId={summary.case_id} />
        </AlertDescription>
      </Alert>
    );
  }
  return null;
}

function CaseBody({ summary, state }: { summary: CaseSummary; state: CaseState }) {
  const usage = usageOf(state.audit);
  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
      <div className="min-w-0 space-y-6">
        <RecommendationCard state={state} />
        <Outcome summary={summary} state={state} />
        <Tabs defaultValue="draft">
          <TabsList className="w-full justify-start overflow-x-auto sm:w-auto">
            <TabsTrigger value="draft">Draft</TabsTrigger>
            <TabsTrigger value="findings">
              Findings <Count value={state.findings.length} />
            </TabsTrigger>
            <TabsTrigger value="evidence">
              Evidence <Count value={state.note_facts.length + state.clauses.length} />
            </TabsTrigger>
            <TabsTrigger value="claim">Claim</TabsTrigger>
            <TabsTrigger value="audit">
              Audit <Count value={state.audit.length} />
            </TabsTrigger>
          </TabsList>
          <TabsContent value="draft">
            <DraftView state={state} />
          </TabsContent>
          <TabsContent value="findings">
            <FindingsView state={state} />
          </TabsContent>
          <TabsContent value="evidence">
            <EvidenceView state={state} />
          </TabsContent>
          <TabsContent value="claim">
            <ClaimView input={state.case_input} />
          </TabsContent>
          <TabsContent value="audit">
            <AuditView audit={state.audit} />
          </TabsContent>
        </Tabs>
      </div>

      <aside className="space-y-6" aria-label="Run">
        <Card>
          <CardHeader>
            <CardTitle>Progress</CardTitle>
          </CardHeader>
          <CardContent>
            <RunTimeline audit={state.audit} status={summary.status} />
          </CardContent>
        </Card>

        {state.triage ? (
          <Card>
            <CardHeader>
              <CardTitle>Triage</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between gap-2">
                <ActionBadge action={state.triage.action} />
                <span className="text-xs text-muted-foreground">
                  {formatPercent(state.triage.confidence)} confidence
                </span>
              </div>
              <ul className="list-disc space-y-1.5 pl-4 text-sm text-muted-foreground">
                {state.triage.reasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            </CardContent>
          </Card>
        ) : null}

        <Card>
          <CardHeader>
            <CardTitle>Cost of this run</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-xs text-muted-foreground">Model calls</dt>
                <dd className="tabular-nums">{usage.attempts}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Drafts written</dt>
                <dd className="tabular-nums">{state.writer_attempts}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Tokens in / out</dt>
                <dd className="tabular-nums">
                  {formatCount(usage.inputTokens)} / {formatCount(usage.outputTokens)}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Model time</dt>
                <dd className="tabular-nums">{formatDuration(usage.latencyMs)}</dd>
              </div>
            </dl>
          </CardContent>
        </Card>
      </aside>
    </div>
  );
}

function Count({ value }: { value: number }) {
  return <span className="rounded-full bg-muted px-1.5 text-[11px] text-muted-foreground tabular-nums">{value}</span>;
}

function CaseSkeleton() {
  return (
    <div className="space-y-6" aria-busy="true" aria-label="Loading case">
      <div className="space-y-2">
        <Skeleton className="h-4 w-48" />
        <Skeleton className="h-8 w-80" />
        <Skeleton className="h-4 w-96 max-w-full" />
      </div>
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="space-y-4">
          <Skeleton className="h-9 w-96 max-w-full" />
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
        <Skeleton className="h-96 w-full" />
      </div>
    </div>
  );
}
