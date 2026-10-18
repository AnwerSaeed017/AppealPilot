import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RunTimeline } from "@/components/case/run-timeline";

import { caseState } from "../../fixtures";

describe("RunTimeline", () => {
  it("tells assistive technology where each step stands", () => {
    const state = caseState("case-timely-filing");
    render(<RunTimeline audit={state.audit} status="FAILED" />);

    const list = screen.getByRole("list", { name: "Workflow progress" });
    expect(list).toHaveTextContent("Rules: done");
    expect(list).toHaveTextContent("Record review: stopped here");
    expect(list).toHaveTextContent("Triage: not started");
  });

  it("shows how often a step ran", () => {
    const state = caseState("case-bone-density-unverified");
    render(<RunTimeline audit={state.audit} status="AWAITING_APPROVAL" />);

    expect(screen.getAllByText("×3")).toHaveLength(2);
    expect(screen.getByText(/Decision/)).toHaveTextContent("waiting for a reviewer");
  });
});
