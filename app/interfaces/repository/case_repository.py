from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime

from app.schemas.audit_event import AuditEvent
from app.schemas.case_status import CaseStatus
from app.schemas.case_summary import CaseEvent, CasePage, CaseSnapshot, CaseSummary


class ICaseRepository(ABC):
    """The record of cases and of the steps of their runs."""

    @abstractmethod
    async def save(
        self, snapshot: CaseSnapshot, events: Sequence[AuditEvent], now: datetime
    ) -> None:
        """Create the case or bring it up to date, and add any steps not yet recorded.

        `events` is the case's whole trail so far. Steps already recorded are left as
        they are, so saving the same state twice changes nothing.
        """

    @abstractmethod
    async def set_status(self, case_id: str, status: CaseStatus, now: datetime) -> bool:
        """Change a case's status. Returns False when there is no such case."""

    @abstractmethod
    async def get(self, case_id: str) -> CaseSummary | None:
        """The case, or None when it does not exist."""

    @abstractmethod
    async def list(self, page: int, page_size: int, status: CaseStatus | None) -> CasePage:
        """One page of cases, newest first, optionally of one status only."""

    @abstractmethod
    async def list_events(self, case_id: str, after_sequence: int) -> tuple[CaseEvent, ...]:
        """The recorded steps of a case after the given position, in order."""
