import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { DecisionPanel } from "@/components/case/decision-panel";

const decide = vi.hoisted(() => vi.fn(async () => null));

vi.mock("@/app/cases/actions", () => ({ decide }));

const SUMMARY = "Request a reopening to add modifier 25 to line 1.";

describe("DecisionPanel", () => {
  it("approves by default", () => {
    render(<DecisionPanel caseId="case-1" summary={SUMMARY} unverifiedCount={0} />);

    expect(screen.getByRole("radio", { name: "Approve" })).toBeChecked();
    expect(screen.getByRole("button", { name: "Approve draft" })).toBeEnabled();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });

  it("asks for a reason before rejecting", async () => {
    render(<DecisionPanel caseId="case-1" summary={SUMMARY} unverifiedCount={0} />);

    await userEvent.click(screen.getByRole("radio", { name: "Reject" }));

    const reason = screen.getByRole("textbox", { name: "Why the draft is rejected" });
    expect(reason).toBeRequired();
    expect(screen.getByRole("button", { name: "Reject draft" })).toBeInTheDocument();
  });

  it("starts an edit from the draft's own summary", async () => {
    render(<DecisionPanel caseId="case-1" summary={SUMMARY} unverifiedCount={0} />);

    await userEvent.click(screen.getByRole("radio", { name: "Edit and approve" }));

    expect(screen.getByRole("textbox", { name: "Your wording of the summary" })).toHaveValue(SUMMARY);
  });

  it("warns before an unverified draft is approved", () => {
    render(<DecisionPanel caseId="case-1" summary={SUMMARY} unverifiedCount={2} />);

    expect(screen.getByText("2 assertions failed verification")).toBeInTheDocument();
  });

  it("sends the chosen decision and its reason to the action", async () => {
    render(<DecisionPanel caseId="case-7" summary={SUMMARY} unverifiedCount={0} />);

    await userEvent.click(screen.getByRole("radio", { name: "Reject" }));
    await userEvent.type(screen.getByRole("textbox"), "Routine follow-up only.");
    await userEvent.click(screen.getByRole("button", { name: "Reject draft" }));

    await vi.waitFor(() => expect(decide).toHaveBeenCalledTimes(1));
    const [caseId, , formData] = decide.mock.calls[0] as unknown as [string, unknown, FormData];
    expect(caseId).toBe("case-7");
    expect(formData.get("kind")).toBe("REJECT");
    expect(formData.get("reason")).toBe("Routine follow-up only.");
  });

  it("shows the API's reason when the decision is not recorded", async () => {
    decide.mockResolvedValueOnce({ errors: ["Case case-1 is not waiting for a decision."] } as never);
    render(<DecisionPanel caseId="case-1" summary={SUMMARY} unverifiedCount={0} />);

    await userEvent.click(screen.getByRole("button", { name: "Approve draft" }));

    expect(await screen.findByText("Case case-1 is not waiting for a decision.")).toBeInTheDocument();
  });
});
