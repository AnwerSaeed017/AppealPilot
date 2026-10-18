import { describe, expect, it } from "vitest";

import type { AuditEvent } from "@/lib/api/types";
import { stepProgress } from "@/lib/progress";

import { caseState } from "../../fixtures";

function event(step: string): AuditEvent {
  return { step, at: "2026-10-16T14:00:00Z", summary: `${step} done` };
}

function states(audit: AuditEvent[], status: Parameters<typeof stepProgress>[1]) {
  return Object.fromEntries(stepProgress(audit, status).map((step) => [step.id, step.state]));
}

describe("stepProgress", () => {
  it("marks the step after the last completed one as in progress while running", () => {
    expect(states([event("rules"), event("retrieval")], "RUNNING")).toMatchObject({
      rules: "done",
      retrieval: "done",
      intake: "active",
      triage: "pending",
    });
  });

  it("marks that step as failed when the run stopped", () => {
    expect(states([event("rules"), event("retrieval")], "FAILED")).toMatchObject({
      intake: "failed",
      triage: "pending",
    });
  });

  it("marks a step the run passed over as skipped, not in progress", () => {
    const audit = ["rules", "retrieval", "intake", "triage"].map(event);
    expect(states(audit, "RUNNING")).toMatchObject({
      document_retrieval: "skipped",
      writer: "active",
    });
  });

  it("shows the decision as waiting once the case is ready for review", () => {
    const progress = stepProgress(caseState("case-modifier-25").audit, "AWAITING_APPROVAL");
    expect(progress.at(-1)).toMatchObject({ id: "approval", state: "waiting" });
    expect(progress.filter((step) => step.state === "done")).toHaveLength(9);
  });

  it("counts repeated runs of the writer and the verifier", () => {
    const progress = stepProgress(caseState("case-bone-density-unverified").audit, "AWAITING_APPROVAL");
    expect(progress.find((step) => step.id === "writer")?.runs).toBe(3);
    expect(progress.find((step) => step.id === "verifier")?.lastSummary).toContain("failed");
  });
});
