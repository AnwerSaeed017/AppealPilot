from typing import Any

from app.agents.states.case_state import CaseState
from app.constants.agents import STEP_REVIEW
from app.interfaces.agents.case_node import ICaseNode
from app.interfaces.utilities.clock import IClock
from app.schemas.audit_event import AuditEvent
from app.schemas.case_status import CaseStatus


class ReviewNode(ICaseNode):
    """Marks the case as waiting for a person, and records whether it arrives verified.

    A draft that still fails verification after the allowed rewrites is sent on as
    unverified. Running out of rewrites never counts as passing.
    """

    def __init__(self, clock: IClock) -> None:
        self._clock = clock

    async def run(self, state: CaseState) -> dict[str, Any]:
        verified = state.verification is not None and state.verification.passed
        return {
            "status": CaseStatus.AWAITING_APPROVAL,
            "audit": (
                AuditEvent(
                    step=STEP_REVIEW,
                    at=self._clock.now(),
                    summary=(
                        "Sent for approval with a verified draft."
                        if verified
                        else (
                            f"Sent for approval UNVERIFIED after {state.writer_attempts} "
                            "drafts; the failing assertions are flagged."
                        )
                    ),
                ),
            ),
        }
