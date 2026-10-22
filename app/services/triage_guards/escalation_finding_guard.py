from collections.abc import Sequence

from app.constants.findings import ESCALATION_FINDINGS
from app.interfaces.service.triage_guard import ITriageGuard
from app.schemas.finding import Finding
from app.schemas.recommended_action import RecommendedAction
from app.schemas.triage_decision import TriageDecision
from app.services.triage_guards.overridden import overridden


class EscalationFindingGuard(ITriageGuard):
    """A finding in ESCALATION_FINDINGS sends the case to a person whatever was chosen.

    Those findings are established by code, and a model has been seen to argue its way
    past a contradiction it was shown.
    """

    def check(self, findings: Sequence[Finding], decision: TriageDecision) -> TriageDecision | None:
        blocking = [finding for finding in findings if finding.code in ESCALATION_FINDINGS]
        if not blocking or decision.action is RecommendedAction.ESCALATE_TO_HUMAN:
            return None
        reasons = tuple(
            f"Escalated by code: {finding.code.value}. {finding.message}" for finding in blocking
        )
        return overridden(decision, RecommendedAction.ESCALATE_TO_HUMAN, reasons)
