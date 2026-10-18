/**
 * Formatting for display. Every function is pure and uses fixed locale and time zone
 * options, so the server and the browser render the same text.
 */

const LOCALE = "en-US";

const money = new Intl.NumberFormat(LOCALE, { style: "currency", currency: "USD" });

const day = new Intl.DateTimeFormat(LOCALE, {
  year: "numeric",
  month: "short",
  day: "numeric",
  timeZone: "UTC",
});

const moment = new Intl.DateTimeFormat(LOCALE, {
  year: "numeric",
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hour12: false,
  timeZone: "UTC",
});

const count = new Intl.NumberFormat(LOCALE);

/** Money arrives from the API as a decimal string, to keep cents exact. */
export function formatMoney(amount: string | number): string {
  const value = typeof amount === "number" ? amount : Number(amount);
  return Number.isFinite(value) ? money.format(value) : String(amount);
}

/** An ISO date ("2026-08-18") as a calendar day. Dates carry no time zone, so none is applied. */
export function formatDate(isoDate: string): string {
  const value = new Date(`${isoDate.slice(0, 10)}T00:00:00Z`);
  return Number.isNaN(value.getTime()) ? isoDate : day.format(value);
}

/** An ISO timestamp, shown in UTC, which is how the API stores it. */
export function formatDateTime(isoDateTime: string): string {
  const value = new Date(isoDateTime);
  return Number.isNaN(value.getTime()) ? isoDateTime : `${moment.format(value)} UTC`;
}

export function formatCount(value: number): string {
  return count.format(value);
}

export function formatDuration(milliseconds: number): string {
  if (milliseconds < 1000) return `${Math.round(milliseconds)} ms`;
  const seconds = milliseconds / 1000;
  return seconds < 60 ? `${seconds.toFixed(1)} s` : `${Math.floor(seconds / 60)} min ${Math.round(seconds % 60)} s`;
}

export function formatPercent(fraction: number): string {
  return `${Math.round(fraction * 100)}%`;
}

/** Whole days from one ISO date to another. */
export function daysBetween(fromIsoDate: string, toIsoDate: string): number {
  const from = Date.parse(`${fromIsoDate.slice(0, 10)}T00:00:00Z`);
  const to = Date.parse(`${toIsoDate.slice(0, 10)}T00:00:00Z`);
  return Math.round((to - from) / 86_400_000);
}
