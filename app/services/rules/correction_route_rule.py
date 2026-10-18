from collections.abc import Sequence

from app.constants.findings import CORRECTABLE_FINDINGS
from app.interfaces.service.finding_rule import IFindingRule
from app.schemas.finding import Finding, FindingCode
from app.schemas.rule_context import RuleContext


class CorrectionRouteRule(IFindingRule):
    """Names the clause that says how a correction is submitted, when one is needed.

    A finding of a correctable error says what to fix; this says through which route the
    payer takes the fix, so the draft can say both. Nothing is reported for a payer whose
    rules name no route.
    """

    def check(self, context: RuleContext, findings: Sequence[Finding]) -> tuple[Finding, ...]:
        clause_id = context.payer_rules.correction_route_clause
        correctable = [finding for finding in findings if finding.code in CORRECTABLE_FINDINGS]
        if clause_id is None or not correctable:
            return ()
        return (
            Finding(
                code=FindingCode.CORRECTION_ROUTE_CLAUSE,
                message=(
                    f"Clause {clause_id} sets how this payer takes a correction to a "
                    "processed claim."
                ),
                clause_ids=(clause_id,),
                line_numbers=tuple(
                    sorted({number for finding in correctable for number in finding.line_numbers})
                ),
            ),
        )
