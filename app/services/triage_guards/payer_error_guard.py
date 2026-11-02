from collections.abc import Sequence

from app.constants.findings import CORRECTABLE_FINDINGS, PAYER_ERROR_FINDINGS
from app.interfaces.service.triage_guard import ITriageGuard
from app.schemas.finding import Finding
from app.schemas.recommended_action import RecommendedAction
from app.schemas.triage_decision import TriageDecision
from app.services.triage_guards.overridden import overridden


class PayerErrorGuard(ITriageGuard):
    """A claim the payer denied in error is appealed.

    When code established that the payer's reason does not hold (no authorization was
    needed, the claim was filed in time, or a document brings it within a filing
    exception) and found nothing in the claim to correct, the remedy is an appeal citing
    the clause the payer misapplied. Requesting documents, writing the amount off or
    resending the same claim would each leave a wrong denial in place. An escalation is
    left alone: a person deciding is never overruled.
    """

    def check(self, findings: Sequence[Finding], decision: TriageDecision) -> TriageDecision | None:
        if decision.action in (
            RecommendedAction.APPEAL_WITH_EVIDENCE,
            RecommendedAction.ESCALATE_TO_HUMAN,
        ):
            return None
        codes = {finding.code for finding in findings}
        payer_errors = codes & PAYER_ERROR_FINDINGS
        if not payer_errors or codes & CORRECTABLE_FINDINGS:
            return None
        names = ", ".join(sorted(code.value for code in payer_errors))
        reason = (
            f"Changed by code: {names} shows the payer's reason does not hold, and no error "
            "in the claim was found to correct, so the remedy is an appeal."
        )
        return overridden(decision, RecommendedAction.APPEAL_WITH_EVIDENCE, (reason,))
