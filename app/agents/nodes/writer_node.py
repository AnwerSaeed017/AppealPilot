from typing import Any

from app.agents.states.case_state import CaseState
from app.constants.agents import STEP_WRITER
from app.core.exceptions import ConflictError
from app.interfaces.agents.case_node import ICaseNode
from app.interfaces.service.writer_agent_service import IWriterAgentService
from app.interfaces.utilities.clock import IClock
from app.schemas.audit_event import AuditEvent


class WriterNode(ICaseNode):
    """Writes the draft, or rewrites it after a failed verification."""

    def __init__(self, writer_agent_service: IWriterAgentService, clock: IClock) -> None:
        self._writer_agent_service = writer_agent_service
        self._clock = clock

    async def run(self, state: CaseState) -> dict[str, Any]:
        if state.triage is None:
            raise ConflictError("The writer cannot run before an action has been chosen.")
        result = await self._writer_agent_service.draft(
            state.case_input,
            state.findings,
            state.clauses,
            state.note_facts,
            state.triage,
            previous=state.draft,
            feedback=state.verification,
        )
        attempt = state.writer_attempts + 1
        return {
            "draft": result.output,
            "writer_attempts": attempt,
            "audit": (
                AuditEvent(
                    step=STEP_WRITER,
                    at=self._clock.now(),
                    summary=(
                        f"Draft {attempt} written with "
                        f"{len(result.output.assertions)} cited assertions."
                    ),
                    llm_call=result.llm_call,
                ),
            ),
        }
