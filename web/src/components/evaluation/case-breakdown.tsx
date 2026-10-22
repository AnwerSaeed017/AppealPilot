import { CircleCheckIcon, CircleXIcon } from "lucide-react";

import { Meter } from "@/components/ui/meter";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { ActionResult, CaseOutcome } from "@/lib/api/types";
import { expectedLabel, formatTally, outcomeLabel, share } from "@/lib/evaluation";

/** Accuracy for each expected action, so a strength in one hides no weakness in another. */
export function ActionBreakdown({ results }: { results: readonly ActionResult[] }) {
  return (
    <div className="divide-y">
      {results.map((result) => (
        <div key={result.expected} className="grid gap-3 py-3 sm:grid-cols-[minmax(0,14rem)_1fr_1fr] sm:items-center">
          <p className="text-sm font-medium">{expectedLabel(result.expected)}</p>
          <Meter
            label="Workflow"
            value={share(result.workflow)}
            valueText={formatTally(result.workflow)}
            tone="success"
          />
          <Meter label="Baseline" value={share(result.baseline)} valueText={formatTally(result.baseline)} />
        </div>
      ))}
    </div>
  );
}

function Outcome({ text, correct }: { text: string; correct: boolean }) {
  const Icon = correct ? CircleCheckIcon : CircleXIcon;
  return (
    <span className={correct ? "inline-flex items-center gap-1.5" : "inline-flex items-center gap-1.5 font-medium text-danger"}>
      <Icon className={correct ? "size-4 text-success" : "size-4"} aria-hidden="true" />
      {text}
      <span className="sr-only">{correct ? "(right)" : "(wrong)"}</span>
    </span>
  );
}

/** Every case at least one system got wrong, with what each did. Nothing is hidden. */
export function CaseOutcomes({ outcomes }: { outcomes: readonly CaseOutcome[] }) {
  if (outcomes.length === 0) {
    return <p className="px-5 py-4 text-sm text-muted-foreground">Both systems got every case right.</p>;
  }
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Case</TableHead>
          <TableHead>Scenario</TableHead>
          <TableHead>Expected</TableHead>
          <TableHead>Workflow</TableHead>
          <TableHead>Baseline</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {outcomes.map((outcome) => (
          <TableRow key={outcome.case_id}>
            <TableCell className="font-mono text-xs">{outcome.case_id}</TableCell>
            <TableCell className="font-mono text-xs text-muted-foreground">{outcome.scenario}</TableCell>
            <TableCell>{expectedLabel(outcome.expected)}</TableCell>
            <TableCell>
              <Outcome text={outcomeLabel(outcome.workflow)} correct={outcome.workflow_correct} />
            </TableCell>
            <TableCell>
              <Outcome text={outcomeLabel(outcome.baseline)} correct={outcome.baseline_correct} />
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
