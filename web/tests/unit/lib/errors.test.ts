import { describe, expect, it } from "vitest";

import { describeFailure, failureFrom } from "@/lib/api/errors";

describe("failureFrom", () => {
  it("reads the API's error envelope", () => {
    const failure = failureFrom(422, {
      success: false,
      error: {
        code: "VALIDATION_FAILED",
        message: "The request is not valid.",
        details: [{ field: "denial.carc_code", message: "String should match pattern" }],
      },
      meta: { timestamp: "2026-10-16T14:00:00Z" },
    });

    expect(failure).toMatchObject({ status: 422, code: "VALIDATION_FAILED" });
    expect(describeFailure(failure)).toEqual(["denial.carc_code: String should match pattern"]);
  });

  it("uses the message when there are no field details", () => {
    const failure = failureFrom(409, {
      success: false,
      error: { code: "CONFLICT", message: "Case is not waiting for a decision.", details: [] },
    });

    expect(describeFailure(failure)).toEqual(["Case is not waiting for a decision."]);
  });

  it("turns any other body into a generic failure", () => {
    const failure = failureFrom(502, "<html>Bad gateway</html>");

    expect(failure.code).toBe("UNEXPECTED_RESPONSE");
    expect(failure.message).toContain("502");
  });

  it("skips malformed details", () => {
    const failure = failureFrom(422, {
      error: { code: "X", message: "Bad", details: [{ nope: true }, { message: "kept" }] },
    });

    expect(describeFailure(failure)).toEqual(["kept"]);
  });
});
