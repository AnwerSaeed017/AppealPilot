from app.constants.modifiers import REPEAT_MODIFIERS
from app.interfaces.service.rule import IRule
from app.schemas.finding import Finding, FindingCode
from app.schemas.rule_context import RuleContext


class RepeatLineRule(IRule):
    """Finds a service billed twice on one claim with no repeat modifier."""

    def check(self, context: RuleContext) -> tuple[Finding, ...]:
        seen: set[tuple[object, ...]] = set()
        repeats: list[int] = []
        for line in context.case_input.claim.lines:
            if REPEAT_MODIFIERS & set(line.modifiers):
                continue
            key = (line.service_date, line.procedure_code, frozenset(line.modifiers))
            if key in seen:
                repeats.append(line.line_number)
            seen.add(key)

        if not repeats:
            return ()
        return (
            Finding(
                code=FindingCode.REPEATED_LINE_WITHOUT_REPEAT_MODIFIER,
                message=(
                    "The same procedure is billed more than once for the same day "
                    "without modifier 76 or 77 on the repeat."
                ),
                clause_ids=(context.payer_rules.repeat_modifier_clause,),
                line_numbers=tuple(repeats),
            ),
        )
