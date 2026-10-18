import type { AuditEvent, CaseStatus } from "./api/types";
import { STEPS, type StepId } from "./labels";

export type StepState = "done" | "active" | "failed" | "waiting" | "skipped" | "pending";

export type StepProgress = {
  id: StepId;
  label: string;
  description: string;
  state: StepState;
  /** How many times the step ran: the writer and verifier can run more than once. */
  runs: number;
  lastSummary: string | null;
  lastAt: string | null;
};

/**
 * Where each workflow step stands, from the audit trail and the case's status.
 *
 * A step with no event before the last completed one was skipped. The first step after
 * it is the one in progress, the one that failed, or the decision the case waits for.
 */
export function stepProgress(audit: readonly AuditEvent[], status: CaseStatus): StepProgress[] {
  const progress: StepProgress[] = STEPS.map((step) => {
    const events = audit.filter((event) => event.step === step.id);
    const last = events.at(-1);
    return {
      id: step.id,
      label: step.label,
      description: step.description,
      state: events.length > 0 ? "done" : "pending",
      runs: events.length,
      lastSummary: last?.summary ?? null,
      lastAt: last?.at ?? null,
    };
  });

  const lastDone = progress.findLastIndex((step) => step.state === "done");
  progress.forEach((step, index) => {
    if (step.state === "pending" && index < lastDone) step.state = "skipped";
  });

  const next = progress.find((step, index) => index > lastDone && step.state === "pending");
  if (next) {
    if (status === "RUNNING") next.state = "active";
    else if (status === "FAILED") next.state = "failed";
    else if (status === "AWAITING_APPROVAL") next.state = "waiting";
  }
  return progress;
}
