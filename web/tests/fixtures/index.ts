/**
 * API responses for tests, built by `scripts/build_web_fixtures.py` from the API's own
 * schemas. Rebuild them after a schema change; never edit the JSON by hand.
 */
import type { CaseEvent } from "./types";
import type { CaseState, CaseView, SampleCase } from "@/lib/api/types";

import cases from "./cases.json";
import runEvents from "./run-events.json";
import samples from "./samples.json";

export const caseViews = cases as unknown as CaseView[];
export const sampleCases = samples as unknown as SampleCase[];
export const runSteps = runEvents as unknown as CaseEvent[];

export function caseView(caseId: string): CaseView {
  const view = caseViews.find((item) => item.summary.case_id === caseId);
  if (!view) throw new Error(`No fixture for case ${caseId}`);
  return view;
}

export function caseState(caseId: string): CaseState {
  const state = caseView(caseId).state;
  if (!state) throw new Error(`Fixture ${caseId} has no state`);
  return state;
}
