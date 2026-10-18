from app.interfaces.service.rule import IRule
from app.schemas.finding import Finding, FindingCode
from app.schemas.rule_context import RuleContext


class NoteDateRule(IRule):
    """Checks that the visit note is dated on a day the claim bills for."""

    def check(self, context: RuleContext) -> tuple[Finding, ...]:
        case_input = context.case_input
        note_date = case_input.visit_note.encounter_date
        if any(line.service_date == note_date for line in case_input.claim.lines):
            return ()
        return (
            Finding(
                code=FindingCode.NOTE_DATE_MISMATCH,
                message=(
                    f"The visit note is dated {note_date.isoformat()}, which is not a "
                    "date of service on the claim."
                ),
            ),
        )
