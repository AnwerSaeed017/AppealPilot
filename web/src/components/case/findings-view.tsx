import { Card, CardContent } from "@/components/ui/card";
import type { CaseState } from "@/lib/api/types";
import { findingLabel } from "@/lib/labels";
import { resolveCitation } from "@/lib/sources";

import { SourceChip } from "./source-chip";

export function FindingsView({ state }: { state: CaseState }) {
  if (state.findings.length === 0) {
    return (
      <p className="py-10 text-center text-sm text-muted-foreground">
        {state.audit.some((event) => event.step === "rules")
          ? "The rules found nothing to report for this claim."
          : "The rules have not run yet."}
      </p>
    );
  }
  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">
        Facts the rules engine established from the claim, the denial and earlier claims. A finding
        states what is true of the data and never recommends an action.
      </p>
      <ul className="space-y-3">
        {state.findings.map((finding, index) => (
          <li key={`${finding.code}-${index}`}>
            <Card>
              <CardContent className="space-y-2 py-4">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-medium">{findingLabel(finding.code)}</p>
                  {(finding.line_numbers ?? []).length > 0 ? (
                    <span className="text-xs text-muted-foreground">
                      Line {(finding.line_numbers ?? []).join(", ")}
                    </span>
                  ) : null}
                </div>
                <p className="text-sm text-muted-foreground">{finding.message}</p>
                {(finding.clause_ids ?? []).length > 0 ? (
                  <div className="flex flex-wrap gap-1.5">
                    {(finding.clause_ids ?? []).map((clauseId) => (
                      <SourceChip
                        key={clauseId}
                        sourceId={clauseId}
                        source={resolveCitation(
                          { kind: "CLAUSE", source_id: clauseId, quote: clauseId },
                          state.case_input,
                          state.clauses,
                        )}
                      />
                    ))}
                  </div>
                ) : null}
              </CardContent>
            </Card>
          </li>
        ))}
      </ul>
    </div>
  );
}
