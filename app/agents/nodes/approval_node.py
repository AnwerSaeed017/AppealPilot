from typing import Any

from langgraph.types import interrupt

from app.agents.states.case_state import CaseState
from app.constants.agents import STEP_APPROVAL
from app.interfaces.agents.case_node import ICaseNode
from app.interfaces.utilities.clock import IClock
from app.schemas.audit_event import AuditEvent
from app.schemas.case_status import CaseStatus
from app.schemas.human_decision import HumanDecision, HumanDecisionKind


class ApprovalNode(ICaseNode):
    """The human gate. The workflow stops here until a reviewer decides.

    Nothing is final before this step, and nothing in a document can skip it: the only
    way past is a decision passed in from outside the workflow.
    """

    def __init__(self, clock: IClock) -> None:
        self._clock = clock

    async def run(self, state: CaseState) -> dict[str, Any]:
        # The first time through, this pauses the workflow. When the workflow is resumed
        # the node runs again from the top and `interrupt` returns the decision.
        answer = interrupt({"case_id": state.case_id, "waiting_for": "human decision"})
        decision = HumanDecision.model_validate(answer)
        rejected = decision.kind is HumanDecisionKind.REJECT
        return {
            "human_decision": decision,
            "status": CaseStatus.REJECTED if rejected else CaseStatus.APPROVED,
            "audit": (
                AuditEvent(
                    step=STEP_APPROVAL,
                    at=self._clock.now(),
                    summary=f"Reviewer decision: {decision.kind.value}.",
                ),
            ),
        }
