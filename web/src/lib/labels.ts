/** Plain-language names for the codes the API uses. One place, so wording stays consistent. */
import type {
  CaseStatus,
  ClauseOrigin,
  FindingCode,
  HumanDecisionKind,
  RecommendedAction,
} from "./api/types";

export type Tone = "neutral" | "info" | "warning" | "success" | "danger";

export const CASE_STATUSES: readonly CaseStatus[] = [
  "RUNNING",
  "AWAITING_APPROVAL",
  "APPROVED",
  "REJECTED",
  "FAILED",
];

export const STATUS: Record<CaseStatus, { label: string; tone: Tone; description: string }> = {
  RUNNING: { label: "Running", tone: "info", description: "The workflow is working on the case." },
  AWAITING_APPROVAL: {
    label: "Needs review",
    tone: "warning",
    description: "A draft is ready and waits for a reviewer's decision.",
  },
  APPROVED: { label: "Approved", tone: "success", description: "A reviewer approved the draft." },
  REJECTED: { label: "Rejected", tone: "neutral", description: "A reviewer rejected the draft." },
  FAILED: {
    label: "Failed",
    tone: "danger",
    description: "The run stopped on an error. It can be retried from its last completed step.",
  },
};

export const ACTION: Record<RecommendedAction, { label: string; description: string }> = {
  CORRECT_AND_RESUBMIT: {
    label: "Correct and resubmit",
    description: "Fix the claim and send it again, or ask the payer to reopen it.",
  },
  APPEAL_WITH_EVIDENCE: {
    label: "Appeal with evidence",
    description: "The record supports the claim; ask the payer to reconsider.",
  },
  REQUEST_DOCUMENTATION: {
    label: "Request documentation",
    description: "Evidence the payer needs is missing from the file.",
  },
  NO_ACTION: {
    label: "No action",
    description: "Nothing the practice can do would change the outcome.",
  },
  ESCALATE_TO_HUMAN: {
    label: "Escalate",
    description: "The case needs a person's judgement before anything is sent.",
  },
};

const PAYER_NAMES: Record<string, string> = {
  MEDICARE: "Medicare",
  TESS: "Tessaly Health Plan",
  QUIL: "Quillon Mutual",
};

/** A payer's display name, or its ID when the name is not known here. */
export function payerName(payerId: string): string {
  return PAYER_NAMES[payerId] ?? payerId;
}

export const DECISION: Record<HumanDecisionKind, string> = {
  APPROVE: "Approved as drafted",
  EDIT_AND_APPROVE: "Approved with edits",
  REJECT: "Rejected",
};

export const CLAUSE_ORIGIN: Record<ClauseOrigin, { label: string; description: string }> = {
  RULE: { label: "Rule", description: "A rule finding cites this clause." },
  SEARCH: { label: "Search", description: "The policy search matched this clause." },
  NEIGHBOUR: { label: "Context", description: "It follows a top clause in the same section." },
  DOCUMENT: {
    label: "Document",
    description: "A search on facts from the supporting documents matched it.",
  },
};

const FINDING_LABELS: Partial<Record<FindingCode, string>> = {
  FILING_LIMIT_EXCEEDED: "Filed after the filing limit",
  FILED_WITHIN_LIMIT: "Filed within the filing limit",
  CORRECTED_CLAIM_WINDOW_CLOSED: "Corrected-claim window closed",
  APPEAL_WINDOW_CLOSED: "Appeal window closed",
  DUPLICATE_OF_PAID_CLAIM: "Duplicate of a paid claim",
  DUPLICATE_OF_DENIED_CLAIM: "Duplicate of a denied claim",
  CHANGED_VERSION_OF_PRIOR_CLAIM: "Changed version of an earlier claim",
  NO_MATCHING_PRIOR_CLAIM: "No matching earlier claim",
  REPEATED_LINE_WITHOUT_REPEAT_MODIFIER: "Repeated line without modifier 76 or 77",
  AUTHORIZATION_NUMBER_MISSING: "Authorization number missing",
  AUTHORIZATION_NOT_REQUIRED: "Authorization not required",
  SIDE_MODIFIER_MISSING: "Side modifier missing",
  VISIT_WITHOUT_MODIFIER_25: "Visit without modifier 25",
  NOTE_DATE_MISMATCH: "Note date differs from the service date",
  PROCEDURE_CONDITIONS_CLAUSE: "Clause setting the procedure's conditions",
  CORRECTION_ROUTE_CLAUSE: "How the payer takes a correction",
  LATERALITY_CONTRADICTION: "The record names both sides of the body",
  DOCUMENT_PATIENT_MISMATCH: "A document describes a different patient",
  CLINICAL_SUPPORT_NEEDS_REVIEW: "Clinical support needs review",
};

export function findingLabel(code: FindingCode): string {
  return FINDING_LABELS[code] ?? humanize(code);
}

/** The workflow's steps, in the order they run. */
export const STEPS = [
  { id: "rules", label: "Rules", description: "Checks the claim against the payer's coded limits." },
  { id: "retrieval", label: "Policy search", description: "Finds the payer clauses that apply." },
  { id: "intake", label: "Record review", description: "Extracts quoted facts from the note." },
  {
    id: "record_checks",
    label: "Record checks",
    description: "Checks the record by code for contradictions a person must resolve.",
  },
  {
    id: "document_retrieval",
    label: "Document search",
    description: "Searches the policy again with facts from the documents.",
  },
  { id: "triage", label: "Triage", description: "Chooses one of the five actions." },
  { id: "writer", label: "Draft", description: "Writes the cited draft." },
  { id: "verifier", label: "Verification", description: "Checks every quote and its meaning." },
  { id: "review", label: "Ready for review", description: "Hands the case to a reviewer." },
  { id: "approval", label: "Decision", description: "The reviewer's decision." },
] as const;

export type StepId = (typeof STEPS)[number]["id"];

export function stepLabel(step: string): string {
  return STEPS.find((item) => item.id === step)?.label ?? humanize(step);
}

/** "VISIT_WITHOUT_MODIFIER_25" -> "Visit without modifier 25". */
export function humanize(code: string): string {
  const words = code.toLowerCase().split("_").join(" ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}
