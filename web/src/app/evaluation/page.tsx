import { FlaskConicalIcon, InfoIcon } from "lucide-react";
import type { Metadata } from "next";
import { Suspense } from "react";

import { ActionBreakdown, CaseOutcomes } from "@/components/evaluation/case-breakdown";
import { ComparisonTable } from "@/components/evaluation/comparison-table";
import { HeadlineComparison } from "@/components/evaluation/headline-comparison";
import { RetrievalBenchmark, VerifierBenchmark } from "@/components/evaluation/stage-benchmarks";
import { PageHeader } from "@/components/page-header";
import { Alert, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/misc";
import { getEvaluations } from "@/lib/api/client";
import { formatTally, significance } from "@/lib/evaluation";
import { formatDateTime } from "@/lib/format";

export const metadata: Metadata = { title: "Evaluation" };

export default function EvaluationPage() {
  return (
    <>
      <PageHeader
        title="Evaluation"
        description="The workflow against a single prompt with the same model and the same policy clauses, on labelled denial cases. Counts, not percentages: the buckets are small."
      />
      <Suspense fallback={<EvaluationSkeleton />}>
        <Results />
      </Suspense>
    </>
  );
}

async function Results() {
  const benchmarks = await getEvaluations();
  if (benchmarks === null) {
    return (
      <Alert tone="info">
        <InfoIcon aria-hidden="true" />
        <AlertTitle>No evaluation results have been published yet.</AlertTitle>
      </Alert>
    );
  }
  const run = benchmarks.run;
  const test = significance(run.paired.p_value);

  return (
    <div className="space-y-8">
      <section aria-labelledby="run-heading" className="space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <FlaskConicalIcon className="size-4 text-primary" aria-hidden="true" />
          <h2 id="run-heading" className="text-base font-semibold">
            {run.title}
          </h2>
          <Badge tone="outline">{run.labelled_cases + run.invalid_cases} cases</Badge>
          <Badge tone="outline">{run.split} set</Badge>
        </div>
        <p className="max-w-4xl text-sm text-muted-foreground text-pretty">{run.summary}</p>
        <p className="text-xs text-muted-foreground">
          Agents {run.agent_model} · judge {run.judge_model} · run {formatDateTime(run.started_at)} ·
          published {formatDateTime(benchmarks.published_at)}
        </p>
      </section>

      <HeadlineComparison run={run} />

      <Card>
        <CardHeader>
          <CardTitle>Is the difference real?</CardTitle>
          <CardDescription>
            On the {run.paired.cases} cases both systems ran, the workflow alone was right on{" "}
            {run.paired.workflow_only} and the baseline alone on {run.paired.baseline_only}. An exact McNemar
            test on those disagreements gives {test.text}.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Badge tone={test.significant ? "success" : "warning"}>
            {test.significant ? "Statistically significant" : "Not yet statistically significant"}
          </Badge>
          <p className="mt-2 text-sm text-muted-foreground">
            The safety difference matters more than the accuracy gap: unsafe actions{" "}
            {formatTally(run.unsafe.workflow)} for the workflow against {formatTally(run.unsafe.baseline)} for the
            baseline.
          </p>
        </CardContent>
      </Card>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card className="overflow-hidden">
          <CardHeader>
            <CardTitle>Every measure</CardTitle>
            <CardDescription>The better side of each measure is highlighted. Cost is reported, not scored.</CardDescription>
          </CardHeader>
          <ComparisonTable run={run} />
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>By expected action</CardTitle>
            <CardDescription>A strength on one action cannot hide a weakness on another.</CardDescription>
          </CardHeader>
          <CardContent>
            <ActionBreakdown results={run.by_action} />
          </CardContent>
        </Card>
      </div>

      <Card className="overflow-hidden">
        <CardHeader>
          <CardTitle>Cases either system got wrong</CardTitle>
          <CardDescription>
            Every miss, for both systems. A conservative miss (asking for documents) is a different kind of error
            from an unsupported appeal.
          </CardDescription>
        </CardHeader>
        <CaseOutcomes outcomes={run.misses} />
      </Card>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card className="overflow-hidden">
          <CardHeader>
            <CardTitle>Verifier: planted errors</CardTitle>
            <CardDescription>Drafts with one deliberate error each, checked by the code stage alone.</CardDescription>
          </CardHeader>
          <VerifierBenchmark verifier={benchmarks.verifier} />
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Policy retrieval</CardTitle>
            <CardDescription>Whether the clauses each case needs are found.</CardDescription>
          </CardHeader>
          <RetrievalBenchmark retrieval={benchmarks.retrieval} />
        </Card>
      </div>

    </div>
  );
}

function EvaluationSkeleton() {
  return (
    <div className="space-y-6" aria-hidden="true">
      <Skeleton className="h-6 w-80" />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }, (_, index) => (
          <Skeleton key={index} className="h-48 rounded-xl" />
        ))}
      </div>
      <Skeleton className="h-40 rounded-xl" />
    </div>
  );
}
