from app.constants.denial_codes import CLINICAL_DENIAL_QUESTIONS
from app.interfaces.service.rule import IRule
from app.schemas.finding import Finding, FindingCode
from app.schemas.rule_context import RuleContext


class ClinicalReviewRule(IRule):
    """Marks denials that turn on clinical support, so that nothing downstream
    mistakes the absence of a rule finding for an answer."""

    def check(self, context: RuleContext) -> tuple[Finding, ...]:
        question = CLINICAL_DENIAL_QUESTIONS.get(context.case_input.denial.carc_code)
        if question is None:
            return ()
        return (
            Finding(
                code=FindingCode.CLINICAL_SUPPORT_NEEDS_REVIEW,
                message=(
                    f"The denial turns on {question}. No rule decides that; it needs "
                    "evidence from the record."
                ),
                line_numbers=tuple(line.line_number for line in context.denied_lines()),
            ),
        )
