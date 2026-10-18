import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/misc";
import type { SampleCase } from "@/lib/api/types";
import { formatDate, formatMoney } from "@/lib/format";
import { payerName } from "@/lib/labels";

import { RunSampleButton } from "./run-sample-button";

export function SampleCard({ sample }: { sample: SampleCase }) {
  const { claim, denial } = sample.input;
  const codes = [`${denial.group_code}-${denial.carc_code}`, ...(denial.rarc_codes ?? [])];
  const procedures = claim.lines.map((line) => line.procedure_code).join(", ");
  return (
    <Card className="relative flex flex-col overflow-hidden transition-all hover:-translate-y-0.5 hover:shadow-lg">
      <div aria-hidden="true" className="h-1 bg-gradient-to-r from-primary via-primary/70 to-cta/70" />
      <CardHeader>
        <div className="flex flex-wrap gap-1.5">
          <Badge tone="info">{claim.payer_id === "MEDICARE" ? "Medicare Part B" : payerName(claim.payer_id)}</Badge>
          {codes.map((code) => (
            <Badge key={code} tone="outline" className="font-mono">
              {code}
            </Badge>
          ))}
        </div>
        <CardTitle className="pt-2 text-base">{sample.title}</CardTitle>
        <CardDescription>{sample.summary}</CardDescription>
      </CardHeader>
      <CardContent className="mt-auto">
        <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
          <div>
            <dt className="text-muted-foreground">Procedures</dt>
            <dd className="font-mono">{procedures}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Denied</dt>
            <dd className="tabular-nums">{formatMoney(denial.denied_amount)}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Denial date</dt>
            <dd>{formatDate(denial.denial_date)}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Documents</dt>
            <dd>{1 + (sample.input.supporting_documents?.length ?? 0)}</dd>
          </div>
        </dl>
      </CardContent>
      <CardFooter>
        <RunSampleButton sampleId={sample.sample_id} title={sample.title} />
      </CardFooter>
    </Card>
  );
}

export function SampleCardSkeleton() {
  return (
    <div className="space-y-3 rounded-xl border bg-card p-5">
      <div className="flex gap-1.5">
        <Skeleton className="h-5 w-24 rounded-full" />
        <Skeleton className="h-5 w-14 rounded-full" />
      </div>
      <Skeleton className="h-5 w-3/4" />
      <Skeleton className="h-12 w-full" />
      <Skeleton className="h-9 w-full" />
    </div>
  );
}
