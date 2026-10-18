from app.constants.modifiers import SIDE_MODIFIERS
from app.interfaces.service.rule import IRule
from app.schemas.finding import Finding, FindingCode
from app.schemas.rule_context import RuleContext


class SideModifierRule(IRule):
    """Finds procedures on a paired joint or limb billed without a side.

    Whether a side on the claim agrees with the record is left to review.
    """

    def check(self, context: RuleContext) -> tuple[Finding, ...]:
        rules = context.payer_rules
        missing = tuple(
            line.line_number
            for line in context.case_input.claim.lines
            if line.procedure_code in rules.side_modifier_codes
            and not SIDE_MODIFIERS & set(line.modifiers)
        )
        if not missing:
            return ()
        return (
            Finding(
                code=FindingCode.SIDE_MODIFIER_MISSING,
                message="A procedure that requires a side modifier is billed without one.",
                clause_ids=(rules.side_modifier_clause,),
                line_numbers=missing,
            ),
        )
