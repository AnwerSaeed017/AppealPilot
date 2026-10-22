from app.constants.denial_codes import FILING_LIMIT_EXPIRED
from app.interfaces.service.rule import IRule
from app.schemas.finding import Finding, FindingCode
from app.schemas.rule_context import RuleContext


class FilingLimitRule(IRule):
    """Compares the days from the service to receipt with the payer's filing limit."""

    def check(self, context: RuleContext) -> tuple[Finding, ...]:
        claim = context.case_input.claim
        rules = context.payer_rules
        service_date = max(line.service_date for line in claim.lines)
        days = (claim.submitted_date - service_date).days

        limit, clause_id = rules.filing_limit_days, rules.filing_limit_clause
        earlier = rules.earlier_filing_limit
        if earlier is not None and service_date < earlier.service_before:
            limit, clause_id = earlier.days, earlier.clause_id

        if days > limit:
            return (
                Finding(
                    code=FindingCode.FILING_LIMIT_EXCEEDED,
                    message=(
                        f"The claim's submission date is {days} days after the service; "
                        f"the filing limit is {limit} days. The denial stands unless the "
                        "record documents an exception the payer's policy lists, or proof "
                        "that an earlier filing was accepted in time."
                    ),
                    clause_ids=(clause_id,),
                ),
            )
        if context.case_input.denial.carc_code == FILING_LIMIT_EXPIRED:
            return (
                Finding(
                    code=FindingCode.FILED_WITHIN_LIMIT,
                    message=(
                        f"The claim was submitted {days} days after the service, inside "
                        f"the filing limit of {limit} days that applies to that date."
                    ),
                    clause_ids=(clause_id,),
                ),
            )
        return ()
