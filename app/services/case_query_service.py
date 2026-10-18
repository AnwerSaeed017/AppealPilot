from collections.abc import Sequence

from app.constants.denial_codes import DENIAL_DESCRIPTIONS, MODIFIER_PROBLEM
from app.interfaces.service.case_query_service import ICaseQueryService
from app.schemas.case_input import CaseInput
from app.schemas.finding import Finding


class CaseQueryService(ICaseQueryService):
    """Builds the search text from what the payer said and what the claim billed.

    With `include_visit_note` the note is added too. That brings in the clinical terms
    a coverage clause uses, at the cost of letting untrusted text influence which
    clauses are found. It can never reach another payer's clauses.
    """

    def __init__(self, include_visit_note: bool) -> None:
        self._include_visit_note = include_visit_note

    def build(self, case_input: CaseInput, findings: Sequence[Finding]) -> str:
        denial = case_input.denial
        denied = set(denial.denied_line_numbers)
        parts = [DENIAL_DESCRIPTIONS.get(denial.carc_code, ""), denial.payer_remark or ""]
        for line in case_input.claim.lines:
            if not denied or line.line_number in denied:
                parts.append(f"procedure code {line.procedure_code}")
                # Billed modifiers belong in the search only when they are what was
                # denied. Otherwise they pull modifier clauses into unrelated cases.
                if denial.carc_code == MODIFIER_PROBLEM:
                    parts.extend(f"modifier {modifier}" for modifier in line.modifiers)
        parts.extend(finding.message for finding in findings)
        if self._include_visit_note:
            parts.append(case_input.visit_note.text)
        return "\n".join(part for part in parts if part)
