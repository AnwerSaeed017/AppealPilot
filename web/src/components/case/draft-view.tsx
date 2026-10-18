import { CircleCheckIcon, CircleXIcon, ClipboardListIcon, WrenchIcon } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { AssertionVerdict, CaseState } from "@/lib/api/types";
import { resolveCitation } from "@/lib/sources";

import { SourceChip } from "./source-chip";

function verdictFor(verdicts: AssertionVerdict[] | undefined, index: number) {
  return verdicts?.find((verdict) => verdict.assertion_index === index);
}

export function DraftView({ state }: { state: CaseState }) {
  const { draft, verification } = state;
  if (!draft) {
    return (
      <p className="py-10 text-center text-sm text-muted-foreground">
        {state.status === "RUNNING" ? "The draft appears here once it is written." : "No draft was written."}
      </p>
    );
  }
  const verdicts = verification?.verdicts ?? [];
  const supported = verdicts.filter((verdict) => verdict.supported).length;

  return (
    <div className="space-y-6">
      <section aria-labelledby="summary-heading" className="space-y-2">
        <h3 id="summary-heading" className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
          Summary
        </h3>
        <p className="leading-relaxed text-pretty whitespace-pre-wrap">{draft.summary}</p>
      </section>

      {draft.correction ? (
        <Alert tone="info">
          <WrenchIcon />
          <AlertTitle>Proposed correction</AlertTitle>
          <AlertDescription className="text-foreground whitespace-pre-wrap">{draft.correction}</AlertDescription>
        </Alert>
      ) : null}

      <section aria-labelledby="assertions-heading" className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 id="assertions-heading" className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
            Assertions and their sources
          </h3>
          {verification ? (
            <Badge tone={supported === verdicts.length ? "success" : "danger"}>
              {supported} of {verdicts.length} assertions verified
            </Badge>
          ) : null}
        </div>
        {(draft.assertions ?? []).length === 0 ? (
          <p className="text-sm text-muted-foreground">The draft makes no factual assertions.</p>
        ) : (
          <ol className="space-y-3">
            {(draft.assertions ?? []).map((assertion, index) => {
              const verdict = verdictFor(verdicts, index);
              return (
                <li key={index}>
                  <Card className={verdict && !verdict.supported ? "border-danger/40" : undefined}>
                    <CardContent className="space-y-3 py-4">
                      <div className="flex gap-3">
                        <span className="mt-0.5 text-xs font-medium text-muted-foreground tabular-nums">
                          {index + 1}
                        </span>
                        <p className="flex-1 text-sm leading-relaxed">{assertion.text}</p>
                        {verdict ? (
                          verdict.supported ? (
                            <CircleCheckIcon className="size-4 shrink-0 text-success" aria-label="Verified" />
                          ) : (
                            <CircleXIcon className="size-4 shrink-0 text-danger" aria-label="Not verified" />
                          )
                        ) : null}
                      </div>
                      <ul className="space-y-1.5 pl-6" aria-label="Sources">
                        {assertion.citations.map((citation, citationIndex) => (
                          <li key={citationIndex} className="flex min-w-0 items-start gap-2">
                            <SourceChip
                              sourceId={citation.source_id}
                              source={resolveCitation(citation, state.case_input, state.clauses)}
                              quote={citation.quote}
                              failed={verdict ? !verdict.supported : false}
                            />
                            <q className="line-clamp-2 min-w-0 pt-px text-xs text-muted-foreground italic">
                              {citation.quote}
                            </q>
                          </li>
                        ))}
                      </ul>
                      {verdict && !verdict.supported && (verdict.problems ?? []).length > 0 ? (
                        <ul className="space-y-1 pl-6 text-xs text-danger">
                          {(verdict.problems ?? []).map((problem) => (
                            <li key={problem}>{problem}</li>
                          ))}
                        </ul>
                      ) : null}
                    </CardContent>
                  </Card>
                </li>
              );
            })}
          </ol>
        )}
      </section>

      {(draft.missing_evidence ?? []).length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ClipboardListIcon className="size-4 text-warning" aria-hidden="true" /> Missing evidence
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="list-disc space-y-1 pl-5 text-sm">
              {(draft.missing_evidence ?? []).map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
