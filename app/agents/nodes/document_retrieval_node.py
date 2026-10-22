from typing import Any

from app.agents.states.case_state import CaseState
from app.constants.agents import STEP_DOCUMENT_RETRIEVAL
from app.interfaces.agents.case_node import ICaseNode
from app.interfaces.service.case_retrieval_service import ICaseRetrievalService
from app.interfaces.utilities.clock import IClock
from app.schemas.audit_event import AuditEvent
from app.schemas.case_clause import ClauseOrigin


class DocumentRetrievalNode(ICaseNode):
    """Looks for clauses that the supporting documents point to. No model is called.

    The first search knows only the claim and the denial. Once intake has read the
    documents, this step searches again with what they say, so that a clause on, say,
    proof of filing is in front of triage when a filing report is on file.
    """

    def __init__(self, case_retrieval_service: ICaseRetrievalService, clock: IClock) -> None:
        self._case_retrieval_service = case_retrieval_service
        self._clock = clock

    async def run(self, state: CaseState) -> dict[str, Any]:
        clauses = await self._case_retrieval_service.extend(
            state.case_input, state.clauses, state.note_facts, state.findings
        )
        before = {item.clause.clause_id for item in state.clauses}
        new = [item for item in clauses if item.clause.clause_id not in before]
        cited = [item.clause.clause_id for item in new if item.origin is ClauseOrigin.RULE]
        added = [item.clause.clause_id for item in new if item.origin is ClauseOrigin.DOCUMENT]
        parts = [
            f"Clauses cited by the record checks: {', '.join(cited)}." if cited else "",
            (
                f"Clauses added from the supporting documents: {', '.join(added)}."
                if added
                else "No clauses added from the supporting documents."
            ),
        ]
        return {
            "clauses": clauses,
            "audit": (
                AuditEvent(
                    step=STEP_DOCUMENT_RETRIEVAL,
                    at=self._clock.now(),
                    summary=" ".join(part for part in parts if part),
                ),
            ),
        }
