import type { Metadata } from "next";
import { connection } from "next/server";
import { Suspense } from "react";

import { PageHeader } from "@/components/page-header";
import { JsonCaseForm } from "@/components/samples/json-case-form";
import { PipelineHero } from "@/components/samples/pipeline-hero";
import { SampleCard, SampleCardSkeleton } from "@/components/samples/sample-card";
import { listSamples } from "@/lib/api/client";

export const metadata: Metadata = { title: "New case" };

export default function NewCasePage() {
  return (
    <>
      <PageHeader
        title="New case"
        description="Run a Medicare sample, or paste a denied claim of your own."
      />
      <PipelineHero />
      <section aria-labelledby="samples-heading" className="mt-10 space-y-3">
        <div>
          <h2 id="samples-heading" className="text-sm font-semibold">
            Sample cases
          </h2>
          <p className="text-sm text-muted-foreground">
            Medicare Part B claims with the payer&apos;s real denial codes and policy text. The
            patients are invented, and the dates move so each deadline is as near today as it was
            when the case was written.
          </p>
        </div>
        <Suspense
          fallback={
            <div className="grid gap-4 md:grid-cols-3">
              <SampleCardSkeleton />
              <SampleCardSkeleton />
              <SampleCardSkeleton />
            </div>
          }
        >
          <Samples />
        </Suspense>
      </section>
      <section aria-labelledby="own-heading" className="mt-10 space-y-3">
        <div>
          <h2 id="own-heading" className="text-sm font-semibold">
            Your own case
          </h2>
          <p className="text-sm text-muted-foreground">
            The claim, the remittance denial and the visit note as JSON, in the shape the API
            documents for <code className="font-mono text-xs">POST /cases</code>. Use synthetic
            data only.
          </p>
        </div>
        <JsonCaseForm />
      </section>
    </>
  );
}

async function Samples() {
  // Samples are re-dated to today on every request, so they are never prerendered.
  await connection();
  const samples = await listSamples();
  return (
    <div className="grid gap-4 md:grid-cols-3">
      {samples.map((sample) => (
        <SampleCard key={sample.sample_id} sample={sample} />
      ))}
    </div>
  );
}
