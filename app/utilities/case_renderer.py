import json
from collections.abc import Sequence

from app.constants.agents import (
    DOCUMENT_CLOSE,
    DOCUMENT_LINE,
    DOCUMENT_OPEN,
    LINE_NUMBER_MARKER,
    NOTHING,
)
from app.interfaces.utilities.case_renderer import ICaseRenderer
from app.schemas.case_clause import CaseClause
from app.schemas.case_input import CaseInput
from app.schemas.code_types import VISIT_NOTE_DOCUMENT_ID
from app.schemas.finding import Finding
from app.schemas.note_fact import NoteFact


class CaseRenderer(ICaseRenderer):
    def structured_data(self, case_input: CaseInput) -> str:
        data = case_input.model_dump(
            mode="json", include={"claim", "denial", "prior_claims"}, exclude_none=True
        )
        return json.dumps(data, indent=2)

    def without_line_numbers(self, quote: str) -> str:
        return LINE_NUMBER_MARKER.sub("", quote).strip()

    def documents(self, case_input: CaseInput) -> str:
        documents = [(VISIT_NOTE_DOCUMENT_ID, "VISIT_NOTE", case_input.visit_note.text)]
        documents += [
            (document.document_id, document.kind.value, document.text)
            for document in case_input.supporting_documents
        ]
        return "\n\n".join(self._document(*document) for document in documents)

    def findings(self, findings: Sequence[Finding]) -> str:
        if not findings:
            return NOTHING
        return "\n".join(
            f"- {finding.code.value}: {finding.message}"
            + (f" (clauses: {', '.join(finding.clause_ids)})" if finding.clause_ids else "")
            for finding in findings
        )

    def clauses(self, clauses: Sequence[CaseClause]) -> str:
        if not clauses:
            return NOTHING
        return "\n\n".join(
            f"[{item.clause.clause_id}] {item.clause.policy_title}: "
            f"{item.clause.section_heading}\n{item.clause.text}"
            for item in clauses
        )

    def note_facts(self, note_facts: Sequence[NoteFact]) -> str:
        if not note_facts:
            return NOTHING
        return "\n".join(
            f"- {'[hedged] ' if fact.hedged else ''}{fact.statement} "
            f'({fact.document_id} line {fact.line_number}: "{fact.quote}")'
            for fact in note_facts
        )

    def fact_pointers(self, note_facts: Sequence[NoteFact]) -> str:
        if not note_facts:
            return NOTHING
        return "\n".join(
            f"- {'[hedged] ' if fact.hedged else ''}{fact.statement} "
            f"({fact.document_id} line {fact.line_number})"
            for fact in note_facts
        )

    @staticmethod
    def _document(document_id: str, kind: str, text: str) -> str:
        # Every line carries its number, so text inside a document that imitates the
        # closing marker still reads as a numbered line of that document.
        lines = [
            DOCUMENT_LINE.format(number=number, text=line)
            for number, line in enumerate(text.splitlines(), start=1)
        ]
        return "\n".join(
            [DOCUMENT_OPEN.format(document_id=document_id, kind=kind), *lines, DOCUMENT_CLOSE]
        )
