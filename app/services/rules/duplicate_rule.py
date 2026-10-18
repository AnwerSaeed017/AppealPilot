from app.constants.denial_codes import DUPLICATE_CLAIM
from app.interfaces.service.rule import IRule
from app.schemas.claim import ClaimLine
from app.schemas.finding import Finding, FindingCode
from app.schemas.prior_claim import PriorClaim, PriorClaimOutcome
from app.schemas.rule_context import RuleContext


def _same_service(a: ClaimLine, b: ClaimLine) -> bool:
    return a.service_date == b.service_date and a.procedure_code == b.procedure_code


def _identical(a: ClaimLine, b: ClaimLine) -> bool:
    return _same_service(a, b) and set(a.modifiers) == set(b.modifiers) and a.units == b.units


class DuplicateRule(IRule):
    """Matches the denied lines against claims the payer has already processed."""

    def check(self, context: RuleContext) -> tuple[Finding, ...]:
        case_input = context.case_input
        findings: list[Finding] = []
        for line in context.denied_lines():
            for prior in case_input.prior_claims:
                finding = self._compare(line, prior, context)
                if finding is not None:
                    findings.append(finding)

        if not findings and case_input.denial.carc_code == DUPLICATE_CLAIM:
            findings.append(
                Finding(
                    code=FindingCode.NO_MATCHING_PRIOR_CLAIM,
                    message="No earlier claim on file matches the lines denied as duplicates.",
                    line_numbers=tuple(line.line_number for line in context.denied_lines()),
                )
            )
        return tuple(findings)

    @staticmethod
    def _compare(line: ClaimLine, prior: PriorClaim, context: RuleContext) -> Finding | None:
        rules = context.payer_rules
        if any(_identical(line, prior_line) for prior_line in prior.lines):
            if prior.outcome is PriorClaimOutcome.PAID:
                return Finding(
                    code=FindingCode.DUPLICATE_OF_PAID_CLAIM,
                    message=f"Line {line.line_number} matches a line paid on {prior.claim_id}.",
                    clause_ids=(rules.duplicate_paid_clause,),
                    line_numbers=(line.line_number,),
                )
            reason = (
                f"reason code {prior.carc_code}" if prior.carc_code else "no reason code on file"
            )
            return Finding(
                code=FindingCode.DUPLICATE_OF_DENIED_CLAIM,
                message=(
                    f"Line {line.line_number} matches a line on {prior.claim_id}, "
                    f"which was denied with {reason}."
                ),
                clause_ids=(
                    (rules.duplicate_denied_clause,) if rules.duplicate_denied_clause else ()
                ),
                line_numbers=(line.line_number,),
            )

        is_replacement = context.case_input.claim.original_claim_id == prior.claim_id
        if not is_replacement and any(_same_service(line, p) for p in prior.lines):
            return Finding(
                code=FindingCode.CHANGED_VERSION_OF_PRIOR_CLAIM,
                message=(
                    f"Line {line.line_number} is the same service as a line on "
                    f"{prior.claim_id} with different modifiers or units, and the claim "
                    "does not reference that claim as its original."
                ),
                clause_ids=(rules.duplicate_replacement_clause,),
                line_numbers=(line.line_number,),
            )
        return None
