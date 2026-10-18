from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from app.schemas.case_input import CaseInput
from app.schemas.case_status import CaseStatus
from app.schemas.case_summary import CaseEvent, CasePage, CaseSummary, CaseView
from app.schemas.human_decision import HumanDecision


class ICaseService(ABC):
    @abstractmethod
    async def submit(self, case_input: CaseInput) -> CaseView:
        """Open a new case and start running it in the background.

        Returns at once, with the case in the RUNNING status.
        """

    @abstractmethod
    async def get(self, case_id: str) -> CaseView:
        """The case as it stands. Raises NotFoundError when there is no such case."""

    @abstractmethod
    async def list(self, page: int, page_size: int, status: CaseStatus | None) -> CasePage:
        """One page of cases, newest first."""

    @abstractmethod
    async def decide(self, case_id: str, decision: HumanDecision) -> CaseView:
        """Apply a reviewer's decision to a case that is waiting for one.

        Raises NotFoundError for an unknown case, and ConflictError when the case is not
        waiting for a decision.
        """

    @abstractmethod
    async def retry(self, case_id: str) -> CaseView:
        """Continue a failed case from its last completed step, in the background.

        Raises NotFoundError for an unknown case, and ConflictError when the case has
        not failed.
        """

    @abstractmethod
    def follow(self, case_id: str) -> AsyncIterator[CaseEvent | CaseSummary]:
        """The steps of a case as they are recorded, then its summary once it stops
        running. A case that has already stopped yields all its steps and its summary.
        """
