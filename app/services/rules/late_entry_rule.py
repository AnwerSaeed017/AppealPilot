from app.constants.documents import CLINICAL_LATE_ENTRY_KINDS
from app.interfaces.service.rule import IRule
from app.schemas.finding import Finding, FindingCode
from app.schemas.rule_context import RuleContext


class LateEntryRule(IRule):
    """Finds clinical addenda dated after the denial.

    An entry written once the denial is known may add findings that were not recorded
    at the time of service. Whether it can be relied on is for a person to decide, so
    the finding is one that escalates the case. Documents that only report what
    happened elsewhere, such as a clearinghouse report or another payer's statement,
    are not entries in the clinical record and are not flagged.
    """

    def check(self, context: RuleContext) -> tuple[Finding, ...]:
        denial_date = context.case_input.denial.denial_date
        late = [
            document
            for document in context.case_input.supporting_documents
            if document.kind in CLINICAL_LATE_ENTRY_KINDS and document.document_date > denial_date
        ]
        if not late:
            return ()
        clause_id = context.payer_rules.late_entry_clause
        listed = ", ".join(
            f"{document.document_id} ({document.document_date.isoformat()})" for document in late
        )
        return (
            Finding(
                code=FindingCode.LATE_ENTRY_AFTER_DENIAL,
                message=(
                    f"Added to the record after the denial of {denial_date.isoformat()}: "
                    f"{listed}. Findings it adds may not have been recorded at the time "
                    "of service."
                ),
                clause_ids=(clause_id,) if clause_id else (),
            ),
        )
