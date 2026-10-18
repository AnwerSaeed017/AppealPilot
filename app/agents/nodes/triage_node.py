from typing import Any

from app.agents.states.case_state import CaseState
from app.constants.agents import STEP_TRIAGE
from app.interfaces.agents.case_node import ICaseNode
from app.interfaces.service.triage_agent_service import ITriageAgentService
from app.interfaces.utilities.clock import IClock
from app.schemas.audit_event import AuditEvent


class TriageNode(ICaseNode):
    """Chooses one of the five actions for the case."""

    def __init__(self, triage_agent_service: ITriageAgentService, clock: IClock) -> None:
        self._triage_agent_service = triage_agent_service
        self._clock = clock

    async def run(self, state: CaseState) -> dict[str, Any]:
        result = await self._triage_agent_service.decide(
            state.case_input, state.as_of, state.findings, state.clauses, state.note_facts
        )
        decision = result.output
        return {
            "triage": decision,
            "audit": (
                AuditEvent(
                    step=STEP_TRIAGE,
                    at=self._clock.now(),
                    summary=(
                        f"Action chosen: {decision.action.value} "
                        f"(confidence {decision.confidence:.2f})."
                    ),
                    llm_call=result.llm_call,
                ),
            ),
        }
