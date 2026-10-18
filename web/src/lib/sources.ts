import type { CaseClause, CaseInput, Citation } from "./api/types";
import { payerName } from "./labels";

/** The visit note's reserved document ID, as the API defines it. */
export const VISIT_NOTE_ID = "NOTE";

/** What a citation points at, ready to show beside the draft. */
export type CitedSource = {
  kind: "clause" | "document";
  id: string;
  title: string;
  subtitle: string;
  text: string;
  url: string | null;
};

/**
 * Resolves a citation against the case. Only the clauses selected for the case and the
 * case's own documents can be cited, so anything else resolves to null.
 */
export function resolveCitation(
  citation: Citation,
  caseInput: CaseInput,
  clauses: readonly CaseClause[],
): CitedSource | null {
  if (citation.kind === "CLAUSE") {
    const match = clauses.find((item) => item.clause.clause_id === citation.source_id);
    if (!match) return null;
    const { clause } = match;
    return {
      kind: "clause",
      id: clause.clause_id,
      title: clause.section_heading,
      subtitle: `${clause.policy_title} · ${payerName(clause.payer_id)}`,
      text: clause.text,
      url: clause.source_url ?? null,
    };
  }
  if (citation.source_id === VISIT_NOTE_ID) {
    return {
      kind: "document",
      id: VISIT_NOTE_ID,
      title: "Visit note",
      subtitle: `Encounter ${caseInput.visit_note.encounter_date}`,
      text: caseInput.visit_note.text,
      url: null,
    };
  }
  const document = (caseInput.supporting_documents ?? []).find(
    (item) => item.document_id === citation.source_id,
  );
  if (!document) return null;
  return {
    kind: "document",
    id: document.document_id,
    title: document.document_id,
    subtitle: `${document.kind.replaceAll("_", " ").toLowerCase()} · ${document.document_date}`,
    text: document.text,
    url: null,
  };
}
