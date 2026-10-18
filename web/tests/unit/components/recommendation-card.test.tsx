import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RecommendationCard } from "@/components/case/recommendation-card";

import { caseState } from "../../fixtures";

describe("RecommendationCard", () => {
  it("leads with the recommended action, its confidence and what is at stake", () => {
    render(<RecommendationCard state={caseState("case-modifier-25")} />);

    expect(screen.getByText("Correct and resubmit")).toBeInTheDocument();
    expect(screen.getByText("$168.00")).toBeInTheDocument();
    expect(screen.getByRole("meter", { name: "Triage confidence" })).toHaveAttribute("aria-valuetext", "86%");
    expect(screen.getByRole("meter", { name: "Assertions verified" })).toHaveAttribute("aria-valuetext", "5 of 5");
  });

  it("shows a partly verified draft on the meter", () => {
    render(<RecommendationCard state={caseState("case-bone-density-unverified")} />);

    expect(screen.getByText("Appeal with evidence")).toBeInTheDocument();
    expect(screen.getByRole("meter", { name: "Assertions verified" })).toHaveAttribute("aria-valuenow", "3");
  });

  it("shows nothing before triage has chosen an action", () => {
    const { container } = render(<RecommendationCard state={caseState("case-timely-running")} />);

    expect(container).toBeEmptyDOMElement();
  });
});
