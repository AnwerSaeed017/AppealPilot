from app.constants.modifiers import SEPARATE_EVALUATION
from app.constants.procedure_codes import OFFICE_VISIT_CODE
from app.interfaces.service.rule import IRule
from app.schemas.finding import Finding, FindingCode
from app.schemas.rule_context import RuleContext


class VisitModifierRule(IRule):
    """Finds a visit billed with a procedure on the same day without modifier 25.

    This states only that the modifier is absent. Whether the record supports adding
    it is a judgement about the note and is never made here.
    """

    def check(self, context: RuleContext) -> tuple[Finding, ...]:
        lines = context.case_input.claim.lines
        procedure_dates = {
            line.service_date for line in lines if not OFFICE_VISIT_CODE.match(line.procedure_code)
        }
        unmarked = tuple(
            line.line_number
            for line in lines
            if OFFICE_VISIT_CODE.match(line.procedure_code)
            and line.service_date in procedure_dates
            and SEPARATE_EVALUATION not in line.modifiers
        )
        if not unmarked:
            return ()
        return (
            Finding(
                code=FindingCode.VISIT_WITHOUT_MODIFIER_25,
                message=(
                    "A visit is billed on the same day as a procedure without modifier "
                    "25. Whether the record supports the modifier needs review."
                ),
                clause_ids=tuple(
                    clause_id
                    for clause_id in (
                        context.payer_rules.modifier_25_clause,
                        context.payer_rules.modifier_25_unsupported_clause,
                    )
                    if clause_id
                ),
                line_numbers=unmarked,
            ),
        )
