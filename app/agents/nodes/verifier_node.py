from typing import Any

from app.agents.states.case_state import CaseState
from app.constants.agents import STEP_VERIFIER
from app.core.exceptions import ConflictError
from app.interfaces.agents.case_node import ICaseNode
from app.interfaces.service.verifier_service import IVerifierService
from app.interfaces.utilities.clock import IClock
from app.schemas.audit_event import AuditEvent


class VerifierNode(ICaseNode):
    """Checks every assertion of the draft against the sources it cites."""

    def __init__(self, verifier_service: IVerifierService, clock: IClock) -> None:
        self._verifier_service = verifier_service
        self._clock = clock

    async def run(self, state: CaseState) -> dict[str, Any]:
        if state.draft is None:
            raise ConflictError("There is no draft to verify.")
        verification = await self._verifier_service.verify(
            state.draft, state.case_input, state.clauses
        )
        report = verification.report
        failed = len(report.failures())
        return {
            "verification": report,
            "audit": (
                AuditEvent(
                    step=STEP_VERIFIER,
                    at=self._clock.now(),
                    summary=(
                        "Every assertion is supported by its citations."
                        if report.passed
                        else f"{failed} of {len(report.verdicts)} assertions failed verification."
                    ),
                    llm_call=verification.llm_call,
                ),
            ),
        }
