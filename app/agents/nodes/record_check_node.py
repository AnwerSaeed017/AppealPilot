from typing import Any

from app.agents.states.case_state import CaseState
from app.constants.agents import STEP_RECORD_CHECKS
from app.interfaces.agents.case_node import ICaseNode
from app.interfaces.service.record_check_service import IRecordCheckService
from app.interfaces.utilities.clock import IClock
from app.schemas.audit_event import AuditEvent


class RecordCheckNode(ICaseNode):
    """Checks the extracted facts by code, and adds what it finds to the rule findings."""

    def __init__(self, record_check_service: IRecordCheckService, clock: IClock) -> None:
        self._record_check_service = record_check_service
        self._clock = clock

    async def run(self, state: CaseState) -> dict[str, Any]:
        found = self._record_check_service.check(state.case_input, state.note_facts)
        summary = (
            f"Found in the record: {', '.join(finding.code.value for finding in found)}."
            if found
            else "No contradiction in the record that code can see."
        )
        return {
            "findings": (*state.findings, *found),
            "audit": (AuditEvent(step=STEP_RECORD_CHECKS, at=self._clock.now(), summary=summary),),
        }
