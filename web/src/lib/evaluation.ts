/** Pure helpers for the evaluation page: reading counts, comparing the two systems. */
import type { RecommendedAction, Tally, TallyPair } from "./api/types";
import { ACTION, humanize } from "./labels";

/** The share a count is of its total, from 0 to 1; 0 when there is nothing to count. */
export function share(tally: Tally): number {
  return tally.total > 0 ? tally.value / tally.total : 0;
}

/** "44 of 54": counts, not percentages, because the buckets are small. */
export function formatTally(tally: Tally): string {
  return `${tally.value} of ${tally.total}`;
}

export type Better = "workflow" | "baseline" | "even";

/**
 * Which system did better on a measure. For "lower" measures (unsafe actions, errors)
 * fewer is better. Compared by share, so different totals are handled.
 */
export function better(pair: TallyPair, direction: "higher" | "lower" = "higher"): Better {
  const workflow = share(pair.workflow);
  const baseline = share(pair.baseline);
  if (Math.abs(workflow - baseline) < 1e-9) return "even";
  const workflowAhead = direction === "higher" ? workflow > baseline : workflow < baseline;
  return workflowAhead ? "workflow" : "baseline";
}

/** The p-value in words: whether the gap between the systems could be chance. */
export function significance(pValue: number): { text: string; significant: boolean } {
  const shown = pValue < 0.001 ? "p < 0.001" : `p = ${pValue.toFixed(3)}`;
  return pValue < 0.05
    ? { text: `${shown}: unlikely to be chance`, significant: true }
    : { text: `${shown}: not enough disagreements to rule out chance`, significant: false };
}

/** The label for an expected action, including the cases built to be rejected. */
export function expectedLabel(expected: string): string {
  if (expected === "INVALID_INPUT") return "Invalid input (must be rejected)";
  return ACTION[expected as RecommendedAction]?.label ?? humanize(expected);
}

/** The label for what a system did with a case. */
export function outcomeLabel(outcome: string): string {
  if (outcome === "rejected") return "Rejected as invalid";
  if (outcome === "error") return "Stopped on an error";
  if (outcome === "not run") return "Not run";
  return ACTION[outcome as RecommendedAction]?.label ?? humanize(outcome);
}

const PLANTED_ERRORS: Record<string, string> = {
  FABRICATED_QUOTE: "A quote that is not in the source",
  INVENTED_CLAUSE: "A clause that does not exist",
  CLAUSE_NOT_SELECTED: "A real clause not selected for the case",
  NUMBER_CHANGED_IN_QUOTE: "A number changed inside a quote",
  NUMBER_CHANGED_IN_ASSERTION: "A number changed in the statement, quote intact",
  CONCLUSION_ADDED: "A conclusion the quote does not support",
  HEDGE_REMOVED: "“Possible” turned into a certainty",
};

export function plantedErrorLabel(error: string): string {
  return PLANTED_ERRORS[error] ?? humanize(error);
}
