from app.constants.denial_codes import AUTHORIZATION_ABSENT
from app.interfaces.service.rule import IRule
from app.schemas.finding import Finding, FindingCode
from app.schemas.rule_context import RuleContext


class AuthorizationRule(IRule):
    """Checks the claim against the payer's list of services needing authorization.

    Whether an authorization was valid, or an urgent service was notified in time,
    depends on documents and is left to review.
    """

    def check(self, context: RuleContext) -> tuple[Finding, ...]:
        claim = context.case_input.claim
        rules = context.payer_rules
        listed = [
            line
            for line in context.denied_lines()
            if line.procedure_code in rules.authorization_codes
        ]
        line_numbers = tuple(line.line_number for line in listed)

        if listed and claim.place_of_service in rules.authorization_exempt_places:
            return (
                Finding(
                    code=FindingCode.AUTHORIZATION_NOT_REQUIRED,
                    message=(
                        f"The place of service is {claim.place_of_service}, where this "
                        "payer does not require authorization."
                    ),
                    clause_ids=(
                        (rules.authorization_exempt_clause,)
                        if rules.authorization_exempt_clause
                        else ()
                    ),
                    line_numbers=line_numbers,
                ),
            )
        if listed and claim.prior_authorization_number is None:
            return (
                Finding(
                    code=FindingCode.AUTHORIZATION_NUMBER_MISSING,
                    message=(
                        "The claim bills a service on the payer's authorization list "
                        "and carries no authorization number."
                    ),
                    clause_ids=(rules.authorization_clause, rules.authorization_number_clause),
                    line_numbers=line_numbers,
                ),
            )
        if not listed and context.case_input.denial.carc_code == AUTHORIZATION_ABSENT:
            return (
                Finding(
                    code=FindingCode.AUTHORIZATION_NOT_REQUIRED,
                    message=(
                        "None of the denied procedure codes is on the payer's list of "
                        "services that require authorization."
                    ),
                    clause_ids=(rules.authorization_clause,),
                    line_numbers=tuple(line.line_number for line in context.denied_lines()),
                ),
            )
        return ()
