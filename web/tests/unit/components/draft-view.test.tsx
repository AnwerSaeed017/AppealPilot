import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DraftView } from "@/components/case/draft-view";

import { caseState } from "../../fixtures";

describe("DraftView", () => {
  it("shows the summary and every assertion with its sources and quoted words", () => {
    const state = caseState("case-modifier-25");
    render(<DraftView state={state} />);

    expect(screen.getByText(state.draft!.summary)).toBeInTheDocument();
    expect(screen.getByText("5 of 5 assertions verified")).toBeInTheDocument();
    expect(screen.getAllByRole("list", { name: "Sources" })).toHaveLength(5);
    expect(screen.getAllByRole("button", { name: /Open source NOTE/ })).toHaveLength(2);
    expect(screen.getByText("Add amlodipine 5 mg daily.")).toBeInTheDocument();
  });

  it("marks an assertion that failed verification and lists the problem", () => {
    render(<DraftView state={caseState("case-bone-density-unverified")} />);

    expect(screen.getByText("3 of 4 assertions verified")).toBeInTheDocument();
    expect(screen.getByLabelText("Not verified")).toBeInTheDocument();
    expect(screen.getByText(/Quote not found in MEDICARE-COV-2.1/)).toBeInTheDocument();
  });

  it("lists missing evidence", () => {
    render(<DraftView state={caseState("case-bone-density")} />);

    expect(screen.getByRole("heading", { name: /Missing evidence/ })).toBeInTheDocument();
  });

  it("explains an empty draft while the case is still running", () => {
    render(<DraftView state={caseState("case-timely-running")} />);

    expect(screen.getByText("The draft appears here once it is written.")).toBeInTheDocument();
  });
});
