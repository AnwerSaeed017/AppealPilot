import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { EvaluationRun, NumberPair, TallyPair } from "@/lib/api/types";
import { better, formatTally, type Better } from "@/lib/evaluation";
import { formatCount, formatDuration } from "@/lib/format";
import { cn } from "@/lib/utils";

type Row = {
  label: string;
  workflow: string;
  baseline: string;
  ahead: Better | null;
};

function tallyRow(label: string, pair: TallyPair, direction: "higher" | "lower" = "higher"): Row {
  return {
    label,
    workflow: formatTally(pair.workflow),
    baseline: formatTally(pair.baseline),
    ahead: better(pair, direction),
  };
}

function costRow(label: string, pair: NumberPair, format: (value: number) => string): Row {
  // Cost is reported, not scored: the workflow does more work on purpose.
  return { label, workflow: format(pair.workflow), baseline: format(pair.baseline), ahead: null };
}

function rows(run: EvaluationRun): Row[] {
  return [
    tallyRow("Action correct (or an accepted alternative)", run.correct),
    tallyRow("Action exactly as labelled", run.exact),
    tallyRow("Unsafe action (a correction or appeal the label does not support)", run.unsafe, "lower"),
    tallyRow("Cases needing a person that were escalated", run.escalations),
    tallyRow("Declined where nothing should be done", run.declined_when_nothing_to_do),
    tallyRow("Prompt-injection cases handled correctly", run.injections),
    tallyRow("Invalid input rejected before any model call", run.invalid_rejected),
    tallyRow("Stopped on an error", run.errors, "lower"),
    tallyRow("Quotes found word for word in the cited source", run.citations_in_source),
    {
      label: "Drafts that passed both verification stages",
      workflow: formatTally(run.verified_drafts),
      baseline: "not verified",
      ahead: null,
    },
    costRow("Median tokens per case", run.median_tokens, (value) => formatCount(Math.round(value))),
    costRow("Median model calls per case", run.median_model_calls, (value) => formatCount(Math.round(value))),
    costRow("Median model time per case", run.median_model_ms, formatDuration),
  ];
}

/** Every measure for one run, the better side of each marked. */
export function ComparisonTable({ run }: { run: EvaluationRun }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Measure</TableHead>
          <TableHead className="text-right">Workflow</TableHead>
          <TableHead className="text-right">Baseline</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows(run).map((row) => (
          <TableRow key={row.label}>
            <TableCell className="text-pretty">{row.label}</TableCell>
            <TableCell
              className={cn("text-right whitespace-nowrap tabular-nums", row.ahead === "workflow" && "font-semibold text-success")}
            >
              {row.workflow}
            </TableCell>
            <TableCell
              className={cn("text-right whitespace-nowrap tabular-nums", row.ahead === "baseline" && "font-semibold text-success")}
            >
              {row.baseline}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
