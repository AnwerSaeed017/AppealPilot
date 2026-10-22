from app.constants.record_checks import SIDE_WORD
from app.interfaces.service.record_check import IRecordCheck
from app.schemas.finding import Finding, FindingCode
from app.schemas.note_fact import NoteFact
from app.schemas.record_check_context import RecordCheckContext


class LateralityCheck(IRecordCheck):
    """Finds a record that names both sides of the body.

    Only the record is compared with itself. A record that agrees with itself but not
    with the side billed on the claim is a billing error to correct, which the
    side-modifier rule and triage handle; a record that disagrees with itself needs a
    person.
    """

    def check(self, context: RecordCheckContext) -> tuple[Finding, ...]:
        first_by_side: dict[str, NoteFact] = {}
        for fact in context.facts:
            for side in sorted({match.lower() for match in SIDE_WORD.findall(fact.quote)}):
                first_by_side.setdefault(side, fact)
        if len(first_by_side) < 2:
            return ()
        where = "; ".join(
            f'{side}: {fact.document_id} line {fact.line_number}, "{fact.quote}"'
            for side, fact in sorted(first_by_side.items())
        )
        return (
            Finding(
                code=FindingCode.LATERALITY_CONTRADICTION,
                message=f"The record names both sides of the body ({where}).",
            ),
        )
