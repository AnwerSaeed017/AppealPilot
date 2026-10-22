import { Badge } from "@/components/ui/badge";
import { Meter } from "@/components/ui/meter";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { EvaluationBenchmarks } from "@/lib/api/types";
import { formatTally, plantedErrorLabel, share } from "@/lib/evaluation";

/**
 * The verifier's deterministic stage on drafts with planted errors. Errors of meaning are
 * listed too: the code stage is not meant to catch them, and saying so is the point.
 */
export function VerifierBenchmark({ verifier }: { verifier: EvaluationBenchmarks["verifier"] }) {
  return (
    <div className="space-y-4">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Planted error</TableHead>
            <TableHead>Caught by</TableHead>
            <TableHead className="text-right">Code check caught</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {verifier.errors.map((item) => (
            <TableRow key={item.error}>
              <TableCell>{plantedErrorLabel(item.error)}</TableCell>
              <TableCell>
                <Badge tone={item.stage === "code" ? "success" : "info"}>
                  {item.stage === "code" ? "Code check" : "Model judge"}
                </Badge>
              </TableCell>
              <TableCell className="text-right tabular-nums">{formatTally(item.caught)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <p className="px-5 pb-4 text-sm text-muted-foreground">
        Correct drafts wrongly flagged: <span className="font-medium text-foreground">{formatTally(verifier.clean_drafts_flagged)}</span>.
        Errors of meaning pass the code check by design; the independent model judge exists for them.
      </p>
    </div>
  );
}

/** Whether the application's own clause selection finds the clauses each case needs. */
export function RetrievalBenchmark({ retrieval }: { retrieval: EvaluationBenchmarks["retrieval"] }) {
  return (
    <div className="space-y-4 px-5 py-4">
      <Meter
        label={`A labelled clause among the top ${retrieval.cut_off}`}
        value={share(retrieval.any_labelled_clause)}
        valueText={formatTally(retrieval.any_labelled_clause)}
        tone="success"
      />
      <Meter
        label={`Every labelled clause among the top ${retrieval.cut_off}`}
        value={share(retrieval.all_labelled_clauses)}
        valueText={formatTally(retrieval.all_labelled_clauses)}
      />
      <Meter
        label="Labelled clauses found"
        value={share(retrieval.labelled_clauses_found)}
        valueText={formatTally(retrieval.labelled_clauses_found)}
      />
      <p className="text-xs text-muted-foreground">
        Rule-cited clauses first, then keyword (BM25) search, with the application&apos;s own settings. No model is involved,
        so these numbers are exact for the current code.
      </p>
    </div>
  );
}
