from app.interfaces.service.rule import IRule
from app.schemas.finding import Finding, FindingCode
from app.schemas.rule_context import RuleContext


class ResponseWindowRule(IRule):
    """Reports when the time to send a corrected claim or an appeal has run out."""

    def check(self, context: RuleContext) -> tuple[Finding, ...]:
        rules = context.payer_rules
        days = (context.as_of - context.case_input.denial.denial_date).days
        findings: list[Finding] = []

        if days > rules.corrected_claim_days:
            findings.append(
                Finding(
                    code=FindingCode.CORRECTED_CLAIM_WINDOW_CLOSED,
                    message=(
                        f"{days} days have passed since the denial; a corrected claim "
                        f"must be received within {rules.corrected_claim_days} days."
                    ),
                    clause_ids=(rules.corrected_claim_clause,),
                )
            )
        if days > rules.appeal_days:
            findings.append(
                Finding(
                    code=FindingCode.APPEAL_WINDOW_CLOSED,
                    message=(
                        f"{days} days have passed since the denial; an appeal must be "
                        f"received within {rules.appeal_days} days."
                    ),
                    clause_ids=(rules.appeal_clause,),
                )
            )
        return tuple(findings)
