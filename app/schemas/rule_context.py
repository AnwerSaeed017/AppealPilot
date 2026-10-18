from datetime import date

from app.schemas.base_schema import BaseSchema
from app.schemas.case_input import CaseInput
from app.schemas.claim import ClaimLine
from app.schemas.payer_rule_set import PayerRuleSet


class RuleContext(BaseSchema):
    """Everything one rule may look at."""

    case_input: CaseInput
    payer_rules: PayerRuleSet
    # The day the case is being worked on.
    as_of: date

    def denied_lines(self) -> tuple[ClaimLine, ...]:
        """The lines the denial applies to: those it names, or all of them."""
        named = set(self.case_input.denial.denied_line_numbers)
        return tuple(
            line for line in self.case_input.claim.lines if not named or line.line_number in named
        )
