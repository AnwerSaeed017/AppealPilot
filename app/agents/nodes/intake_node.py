from typing import Any

from app.agents.states.case_state import CaseState
from app.constants.agents import STEP_INTAKE
from app.interfaces.agents.case_node import ICaseNode
from app.interfaces.service.intake_agent_service import IIntakeAgentService
from app.interfaces.utilities.clock import IClock
from app.schemas.audit_event import AuditEvent


class IntakeNode(ICaseNode):
    """Extracts facts from the visit note and the supporting documents."""

    def __init__(self, intake_agent_service: IIntakeAgentService, clock: IClock) -> None:
        self._intake_agent_service = intake_agent_service
        self._clock = clock

    async def run(self, state: CaseState) -> dict[str, Any]:
        result = await self._intake_agent_service.extract(state.case_input)
        facts = result.output.facts
        return {
            "note_facts": facts,
            "audit": (
                AuditEvent(
                    step=STEP_INTAKE,
                    at=self._clock.now(),
                    summary=f"{len(facts)} facts extracted from the documents.",
                    llm_call=result.llm_call,
                ),
            ),
        }
