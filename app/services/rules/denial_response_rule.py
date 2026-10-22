from app.interfaces.service.rule import IRule
from app.schemas.finding import Finding, FindingCode
from app.schemas.rule_context import RuleContext


class DenialResponseRule(IRule):
    """Names the payer's clauses on what follows from the denial's reason code.

    The other rules cite the clause that states a requirement. What decides the action
    is often a different clause: that a late-filing denial is final, that no
    authorization is issued after the service, how a medical-necessity denial is
    appealed. The denial's wording matches the first kind, so a keyword search tends to
    miss the second. The payer's rule set lists them per reason code, and this rule
    cites them, which puts them in front of every later step.
    """

    def check(self, context: RuleContext) -> tuple[Finding, ...]:
        carc_code = context.case_input.denial.carc_code
        clause_ids = context.payer_rules.denial_response_clauses.get(carc_code, ())
        if not clause_ids:
            return ()
        return (
            Finding(
                code=FindingCode.DENIAL_RESPONSE_CLAUSES,
                message=(
                    f"For reason code {carc_code}, this payer's clauses "
                    f"{', '.join(clause_ids)} say what follows from the denial: whether it "
                    "is final, and how it may be corrected, appealed or excepted."
                ),
                clause_ids=clause_ids,
                line_numbers=tuple(line.line_number for line in context.denied_lines()),
            ),
        )
