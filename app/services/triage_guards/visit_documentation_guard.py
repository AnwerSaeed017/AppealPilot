from collections.abc import Sequence

from app.interfaces.service.triage_guard import ITriageGuard
from app.schemas.finding import Finding, FindingCode
from app.schemas.recommended_action import RecommendedAction
from app.schemas.triage_decision import TriageDecision
from app.services.triage_guards.overridden import overridden


class VisitDocumentationGuard(ITriageGuard):
    """No request for documentation to support modifier 25: send the case to a person.

    Whether a visit was a significant, separately identifiable service is shown only by
    that visit's own note, which is already in the record. There is nothing else to
    retrieve: asking for more would mean writing it after the denial. Whether the note
    as written is enough is a coding judgement.
    """

    def check(self, findings: Sequence[Finding], decision: TriageDecision) -> TriageDecision | None:
        if decision.action is not RecommendedAction.REQUEST_DOCUMENTATION:
            return None
        if not any(finding.code is FindingCode.VISIT_WITHOUT_MODIFIER_25 for finding in findings):
            return None
        reason = (
            "Escalated by code: support for modifier 25 can only be the visit note of that "
            "date, which is already in the record; requesting more documentation would mean "
            "writing it after the denial. Whether the note supports the modifier is a coding "
            "judgement."
        )
        return overridden(decision, RecommendedAction.ESCALATE_TO_HUMAN, (reason,))
