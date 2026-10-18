import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeAll, describe, expect, it } from "vitest";

import { SourceChip } from "@/components/case/source-chip";
import type { CitedSource } from "@/lib/sources";

const clause: CitedSource = {
  kind: "clause",
  id: "MEDICARE-MOD-1.2",
  title: "Medicare Claims Processing Manual, Chapter 12, §40.1.C Minor Surgeries and Endoscopies",
  subtitle: "Evaluation and Management Services on the Day of a Procedure · MEDICARE",
  text: "Visits by the same physician on the same day as a minor surgery or endoscopy are included in the payment for the procedure, unless a significant, separately identifiable service is also performed.",
  url: "https://www.cms.gov/Regulations-and-Guidance/Guidance/Manuals/downloads/clm104c12.pdf",
};

beforeAll(() => {
  // jsdom has no layout, so scrolling is a no-op here.
  Element.prototype.scrollIntoView = () => {};
});

describe("SourceChip", () => {
  it("opens the full source with the quoted words highlighted", async () => {
    render(<SourceChip sourceId={clause.id} source={clause} quote="separately identifiable service" />);

    await userEvent.click(screen.getByRole("button", { name: "Open source MEDICARE-MOD-1.2" }));

    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText(clause.title)).toBeInTheDocument();
    const mark = dialog.querySelector("mark");
    expect(mark).toHaveTextContent("separately identifiable service");
    expect(within(dialog).queryByText(/do not appear in the source/)).not.toBeInTheDocument();
  });

  it("links to the official source when there is one", async () => {
    render(<SourceChip sourceId={clause.id} source={clause} quote="minor surgery" />);
    await userEvent.click(screen.getByRole("button", { name: /Open source/ }));

    const link = await screen.findByRole("link", { name: /Read it at the source/ });
    expect(link).toHaveAttribute("href", clause.url);
    expect(link).toHaveAttribute("rel", expect.stringContaining("noopener"));
  });

  it("warns when the quoted words are not in the source", async () => {
    render(<SourceChip sourceId={clause.id} source={clause} quote="covered every 12 months" failed />);
    await userEvent.click(screen.getByRole("button", { name: /Open source/ }));

    expect(await screen.findByText("These words do not appear in the source.")).toBeInTheDocument();
    expect(document.querySelector("mark")).toBeNull();
  });

  it("says so when the citation names a source outside the case", async () => {
    render(<SourceChip sourceId="MEDICARE-XX-9.9" source={null} quote="anything" />);
    await userEvent.click(screen.getByRole("button", { name: /Open source/ }));

    expect(await screen.findByRole("heading", { name: "Source not found" })).toBeInTheDocument();
  });
});
