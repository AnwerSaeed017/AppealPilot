from abc import ABC, abstractmethod
from datetime import date

from app.agents.states.case_state import CaseState
from app.schemas.case_input import CaseInput
from app.schemas.human_decision import HumanDecision


class ICaseWorkflow(ABC):
    @abstractmethod
    async def start(self, case_id: str, case_input: CaseInput, as_of: date) -> CaseState:
        """Run a new case until it pauses for approval, and return its state.

        Raises ConflictError when a case with this ID has already been started.
        """

    @abstractmethod
    async def resume(self, case_id: str, decision: HumanDecision) -> CaseState:
        """Apply the reviewer's decision to a paused case and return its final state.

        Raises NotFoundError for an unknown case, and ConflictError when the case is not
        waiting for a decision, so a decision sent twice is applied once.
        """

    @abstractmethod
    async def continue_run(self, case_id: str) -> CaseState:
        """Carry on a case whose run stopped part-way, from its last completed step.

        Raises NotFoundError when nothing was saved for the case, and ConflictError when
        it has no unfinished step, including when it is waiting for a decision.
        """

    @abstractmethod
    async def get(self, case_id: str) -> CaseState | None:
        """The case's current state, or None when it does not exist."""
