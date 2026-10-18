import type { AuditEvent } from "@/lib/api/types";

/** One `step` event of a case's live stream. */
export type CaseEvent = { sequence: number; event: AuditEvent };
