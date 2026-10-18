from typing import Any

from app.agents.states.case_state import CaseState
from app.constants.agents import STEP_RETRIEVAL
from app.interfaces.agents.case_node import ICaseNode
from app.interfaces.service.case_retrieval_service import ICaseRetrievalService
from app.interfaces.utilities.clock import IClock
from app.schemas.audit_event import AuditEvent


class RetrievalNode(ICaseNode):
    """Selects the policy clauses that may be cited for this case. No model is called."""

    def __init__(self, case_retrieval_service: ICaseRetrievalService, clock: IClock) -> None:
        self._case_retrieval_service = case_retrieval_service
        self._clock = clock

    async def run(self, state: CaseState) -> dict[str, Any]:
        clauses = await self._case_retrieval_service.retrieve(state.case_input, state.findings)
        listed = (
            ", ".join(f"{item.clause.clause_id} ({item.origin.value})" for item in clauses)
            or "none"
        )
        return {
            "clauses": clauses,
            "audit": (
                AuditEvent(
                    step=STEP_RETRIEVAL,
                    at=self._clock.now(),
                    summary=f"Clauses selected: {listed}.",
                ),
            ),
        }
