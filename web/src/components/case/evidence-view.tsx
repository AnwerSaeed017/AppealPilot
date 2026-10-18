import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { CaseState } from "@/lib/api/types";
import { CLAUSE_ORIGIN } from "@/lib/labels";
import { resolveCitation } from "@/lib/sources";

import { SourceChip } from "./source-chip";

export function EvidenceView({ state }: { state: CaseState }) {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Facts from the record</CardTitle>
          <CardDescription>
            What the record review took from the note and the documents, each with the exact words it rests on.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {state.note_facts.length === 0 ? (
            <p className="text-sm text-muted-foreground">No facts extracted yet.</p>
          ) : (
            <ul className="divide-y">
              {state.note_facts.map((fact, index) => (
                <li key={index} className="space-y-1.5 py-3 first:pt-0 last:pb-0">
                  <div className="flex flex-wrap items-start gap-2">
                    <p className="flex-1 text-sm">{fact.statement}</p>
                    {fact.hedged ? (
                      <Badge tone="warning" title="The source words this as uncertain.">
                        Hedged
                      </Badge>
                    ) : null}
                  </div>
                  <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                    <SourceChip
                      sourceId={fact.document_id}
                      source={resolveCitation(
                        { kind: "DOCUMENT", source_id: fact.document_id, quote: fact.quote },
                        state.case_input,
                        state.clauses,
                      )}
                      quote={fact.quote}
                    />
                    <span>line {fact.line_number}</span>
                    <span className="truncate italic">“{fact.quote}”</span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Policy clauses for this case</CardTitle>
          <CardDescription>
            Only these clauses may be cited. Each shows why it was selected.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {state.clauses.length === 0 ? (
            <p className="text-sm text-muted-foreground">No clauses selected yet.</p>
          ) : (
            <ol className="divide-y">
              {state.clauses.map(({ clause, rank, origin }) => (
                <li key={clause.clause_id} className="flex gap-3 py-3 first:pt-0 last:pb-0">
                  <span className="mt-0.5 w-5 text-xs text-muted-foreground tabular-nums">{rank}</span>
                  <div className="min-w-0 flex-1 space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <SourceChip
                        sourceId={clause.clause_id}
                        source={resolveCitation(
                          { kind: "CLAUSE", source_id: clause.clause_id, quote: clause.clause_id },
                          state.case_input,
                          state.clauses,
                        )}
                      />
                      <Badge tone="neutral" title={CLAUSE_ORIGIN[origin].description}>
                        {CLAUSE_ORIGIN[origin].label}
                      </Badge>
                    </div>
                    <p className="text-sm font-medium">{clause.section_heading}</p>
                    <p className="line-clamp-2 text-xs text-muted-foreground">{clause.text}</p>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
