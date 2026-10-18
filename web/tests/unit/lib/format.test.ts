import { describe, expect, it } from "vitest";

import {
  daysBetween,
  formatDate,
  formatDateTime,
  formatDuration,
  formatMoney,
  formatPercent,
} from "@/lib/format";

describe("format", () => {
  it("formats money from the API's decimal strings", () => {
    expect(formatMoney("168.00")).toBe("$168.00");
    expect(formatMoney("1234.5")).toBe("$1,234.50");
  });

  it("leaves an unreadable amount as it came", () => {
    expect(formatMoney("n/a")).toBe("n/a");
  });

  it("shows a calendar date without shifting it by a time zone", () => {
    expect(formatDate("2026-01-01")).toBe("Jan 1, 2026");
    expect(formatDate("2026-12-31")).toBe("Dec 31, 2026");
  });

  it("shows timestamps in UTC", () => {
    expect(formatDateTime("2026-10-16T14:02:11Z")).toBe("Oct 16, 2026, 14:02:11 UTC");
  });

  it("formats durations at a readable scale", () => {
    expect(formatDuration(420)).toBe("420 ms");
    expect(formatDuration(7380)).toBe("7.4 s");
    expect(formatDuration(125_000)).toBe("2 min 5 s");
  });

  it("formats fractions as whole percentages", () => {
    expect(formatPercent(0.857)).toBe("86%");
  });

  it("counts whole days between ISO dates", () => {
    expect(daysBetween("2025-08-05", "2026-09-01")).toBe(392);
  });
});
