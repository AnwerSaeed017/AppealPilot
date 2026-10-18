"use server";

import { refresh } from "next/cache";
import { redirect } from "next/navigation";

import { decideCase, listSamples, retryCase, submitCase } from "@/lib/api/client";
import { ApiFailure, ApiUnavailable, describeFailure } from "@/lib/api/errors";
import type { HumanDecision, HumanDecisionKind } from "@/lib/api/types";

/**
 * Server Actions: every change the web app makes goes through one of these, on the
 * server. They pass what the user entered to the API, which owns every validation rule,
 * and turn its errors into messages for the form.
 *
 * This prototype has no sign-in. A deployment would check the reviewer's session at the
 * top of each action before calling the API.
 */

export type FormState = { errors: string[] } | null;

function messagesFor(error: unknown): string[] {
  if (error instanceof ApiFailure) return describeFailure(error);
  if (error instanceof ApiUnavailable) return [error.message];
  throw error;
}

/** Runs one of the sample cases. Only the sample's ID comes from the browser. */
export async function runSample(sampleId: string): Promise<FormState> {
  let caseId: string;
  try {
    const sample = (await listSamples()).find((item) => item.sample_id === sampleId);
    if (!sample) return { errors: ["That sample is no longer available."] };
    caseId = (await submitCase(sample.input)).summary.case_id;
  } catch (error) {
    return { errors: messagesFor(error) };
  }
  redirect(`/cases/${encodeURIComponent(caseId)}`);
}

/** Submits a case written or pasted as JSON. */
export async function submitCaseJson(_previous: FormState, formData: FormData): Promise<FormState> {
  const raw = formData.get("case");
  if (typeof raw !== "string" || raw.trim() === "") {
    return { errors: ["Paste the case as JSON first."] };
  }
  let input: unknown;
  try {
    input = JSON.parse(raw);
  } catch {
    return { errors: ["That is not valid JSON. Check for a missing comma or quote."] };
  }
  let caseId: string;
  try {
    caseId = (await submitCase(input)).summary.case_id;
  } catch (error) {
    return { errors: messagesFor(error) };
  }
  redirect(`/cases/${encodeURIComponent(caseId)}`);
}

const DECISION_KINDS: readonly HumanDecisionKind[] = ["APPROVE", "EDIT_AND_APPROVE", "REJECT"];

function text(formData: FormData, name: string): string | null {
  const value = formData.get(name);
  return typeof value === "string" && value.trim() !== "" ? value.trim() : null;
}

/** Records the reviewer's decision at the approval gate. */
export async function decide(
  caseId: string,
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const kind = formData.get("kind");
  if (typeof kind !== "string" || !DECISION_KINDS.includes(kind as HumanDecisionKind)) {
    return { errors: ["Choose approve, edit, or reject."] };
  }
  const decision: HumanDecision = { kind: kind as HumanDecisionKind };
  if (kind === "REJECT") decision.reason = text(formData, "reason");
  if (kind === "EDIT_AND_APPROVE") decision.edited_summary = text(formData, "edited_summary");
  try {
    await decideCase(caseId, decision);
  } catch (error) {
    return { errors: messagesFor(error) };
  }
  refresh();
  return null;
}

/** Continues a failed case from its last completed step. */
export async function retry(caseId: string): Promise<FormState> {
  try {
    await retryCase(caseId);
  } catch (error) {
    return { errors: messagesFor(error) };
  }
  refresh();
  return null;
}
