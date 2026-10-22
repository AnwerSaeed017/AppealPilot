import { describe, expect, it } from "vitest";

import {
  better,
  expectedLabel,
  formatTally,
  outcomeLabel,
  plantedErrorLabel,
  share,
  significance,
} from "@/lib/evaluation";

describe("tallies", () => {
  it("reads a count as a share of its total", () => {
    expect(share({ value: 44, total: 54 })).toBeCloseTo(0.8148, 3);
    expect(share({ value: 0, total: 0 })).toBe(0);
    expect(formatTally({ value: 44, total: 54 })).toBe("44 of 54");
  });
});

describe("better", () => {
  const pair = (workflow: number, baseline: number) => ({
    workflow: { value: workflow, total: 10 },
    baseline: { value: baseline, total: 10 },
  });

  it("prefers more for measures where higher is better", () => {
    expect(better(pair(8, 6))).toBe("workflow");
    expect(better(pair(6, 8))).toBe("baseline");
    expect(better(pair(7, 7))).toBe("even");
  });

  it("prefers fewer for measures where lower is better", () => {
    expect(better(pair(1, 4), "lower")).toBe("workflow");
  });

  it("compares shares, so different totals are fair", () => {
    const pair = { workflow: { value: 292, total: 292 }, baseline: { value: 189, total: 223 } };
    expect(better(pair)).toBe("workflow");
  });
});

describe("significance", () => {
  it("says when a gap could be chance", () => {
    expect(significance(0.344)).toEqual({
      text: "p = 0.344: not enough disagreements to rule out chance",
      significant: false,
    });
    expect(significance(0.0004).significant).toBe(true);
  });
});

describe("labels", () => {
  it("names expected actions, outcomes and planted errors in plain words", () => {
    expect(expectedLabel("ESCALATE_TO_HUMAN")).toBe("Escalate");
    expect(expectedLabel("INVALID_INPUT")).toBe("Invalid input (must be rejected)");
    expect(outcomeLabel("error")).toBe("Stopped on an error");
    expect(outcomeLabel("NO_ACTION")).toBe("No action");
    expect(plantedErrorLabel("INVENTED_CLAUSE")).toBe("A clause that does not exist");
  });
});
