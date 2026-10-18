import { describe, expect, it } from "vitest";

import { usageOf } from "@/lib/usage";

import { caseState } from "../../fixtures";

describe("usageOf", () => {
  it("sums the model calls of a run and counts re-asks", () => {
    const usage = usageOf(caseState("case-modifier-25").audit);

    expect(usage).toEqual({
      modelSteps: 4,
      attempts: 5,
      inputTokens: 2794 + 3311 + 4120 + 2210,
      outputTokens: 612 + 402 + 1180 + 310,
      latencyMs: 7380 + 4912 + 11204 + 4420,
    });
  });

  it("is zero for a run that has called no model", () => {
    expect(usageOf(caseState("case-timely-filing").audit)).toMatchObject({ attempts: 0, inputTokens: 0 });
  });
});
