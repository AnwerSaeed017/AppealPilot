from abc import ABC, abstractmethod

from app.agents.states.case_state import CaseState
from app.schemas.case_status import CaseStatus


class ICaseProjectionService(ABC):
    """Keeps the case tables in step with a case's working state."""

    @abstractmethod
    async def record(self, state: CaseState) -> None:
        """Write the case as it stands, with any steps not yet recorded.

        Called after every step of a run, so progress is visible while a case runs.
        Recording the same state twice changes nothing.
        """

    @abstractmethod
    async def mark(self, case_id: str, status: CaseStatus) -> bool:
        """Set a case's status directly. Returns False when there is no such case."""
