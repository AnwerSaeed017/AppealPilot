import { describe, expect, it } from "vitest";

import { findQuote, highlightQuote } from "@/lib/quote";

describe("findQuote", () => {
  it("finds an exact quote and returns its range in the original text", () => {
    const source = "Modifier -25 is added to the E/M code on the claim.";
    const range = findQuote(source, "added to the E/M code");

    expect(range).not.toBeNull();
    expect(source.slice(range!.start, range!.end)).toBe("added to the E/M code");
  });

  it("ignores case and runs of whitespace, as the API's citation check does", () => {
    const source = "Visits by the same physician\non the same day   as a minor surgery";
    const range = findQuote(source, "ON THE SAME DAY as a minor");

    expect(source.slice(range!.start, range!.end)).toBe("on the same day   as a minor");
  });

  it("matches a quote that spans a line break in the source", () => {
    const source = "line one ends here\nand line two continues";
    const range = findQuote(source, "ends here and line two");

    expect(source.slice(range!.start, range!.end)).toBe("ends here\nand line two");
  });

  it("ignores typography a model adds: non-breaking hyphens, dashes, curly quotes", () => {
    const source = 'Intra-articular injection; glucose 180-240 mg/dL. The "left" knee.';
    const quote = "Intra\u2011articular injection; glucose 180\u2013240 mg/dL. The \u201cleft\u201d knee.";
    const range = findQuote(source, quote);

    expect(source.slice(range!.start, range!.end)).toBe(source);
  });

  it("still rejects a changed word written with typographic dashes", () => {
    expect(findQuote("glucose 180-240 mg/dL", "glucose 180\u2013250 mg/dL")).toBeNull();
  });

  it("returns null when the words are not in the source", () => {
    expect(findQuote("covered every 23 months", "covered every 12 months")).toBeNull();
  });

  it("returns null for an empty quote", () => {
    expect(findQuote("anything", "   ")).toBeNull();
  });
});

describe("highlightQuote", () => {
  it("splits the source around the quote", () => {
    expect(highlightQuote("before QUOTE after", "quote")).toEqual([
      { text: "before ", highlighted: false },
      { text: "QUOTE", highlighted: true },
      { text: " after", highlighted: false },
    ]);
  });

  it("returns the whole source unhighlighted when the quote is absent", () => {
    expect(highlightQuote("source text", "missing")).toEqual([{ text: "source text", highlighted: false }]);
  });

  it("drops empty segments at either end", () => {
    expect(highlightQuote("whole", "whole")).toEqual([{ text: "whole", highlighted: true }]);
  });
});
