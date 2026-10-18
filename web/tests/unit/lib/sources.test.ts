import { describe, expect, it } from "vitest";

import { resolveCitation, VISIT_NOTE_ID } from "@/lib/sources";

import { caseState } from "../../fixtures";

const state = caseState("case-bone-density");

describe("resolveCitation", () => {
  it("resolves a clause selected for the case, with its official source", () => {
    const source = resolveCitation(
      { kind: "CLAUSE", source_id: "MEDICARE-COV-1.2", quote: "x" },
      state.case_input,
      state.clauses,
    );

    expect(source).toMatchObject({ kind: "clause", id: "MEDICARE-COV-1.2" });
    expect(source?.title).toContain("410.31(c)");
    expect(source?.url).toMatch(/^https:\/\/www\.ecfr\.gov\//);
  });

  it("does not resolve a clause that was not selected for the case", () => {
    expect(
      resolveCitation({ kind: "CLAUSE", source_id: "MEDICARE-TF-1.1", quote: "x" }, state.case_input, state.clauses),
    ).toBeNull();
  });

  it("resolves the visit note", () => {
    const source = resolveCitation(
      { kind: "DOCUMENT", source_id: VISIT_NOTE_ID, quote: "x" },
      state.case_input,
      state.clauses,
    );

    expect(source).toMatchObject({ kind: "document", title: "Visit note", url: null });
    expect(source?.text).toBe(state.case_input.visit_note.text);
  });

  it("resolves a supporting document by its ID", () => {
    const source = resolveCitation(
      { kind: "DOCUMENT", source_id: "RX-HISTORY", quote: "x" },
      state.case_input,
      state.clauses,
    );

    expect(source?.text).toContain("prednisone");
    expect(source?.subtitle).toContain("other");
  });

  it("returns null for an unknown document", () => {
    expect(
      resolveCitation({ kind: "DOCUMENT", source_id: "NOPE", quote: "x" }, state.case_input, state.clauses),
    ).toBeNull();
  });
});
