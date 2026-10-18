"""In-memory stand-ins for interfaces, used in place of real collaborators."""

from collections.abc import Sequence
from datetime import UTC, datetime

from app.interfaces.repository.case_repository import ICaseRepository
from app.interfaces.repository.health_repository import IHealthRepository
from app.interfaces.utilities.clock import IClock
from app.schemas.audit_event import AuditEvent
from app.schemas.case_status import CaseStatus
from app.schemas.case_summary import CaseEvent, CasePage, CaseSnapshot, CaseSummary

FIXED_NOW = datetime(2026, 10, 12, 9, 30, tzinfo=UTC)


class FixedClock(IClock):
    def __init__(self, now: datetime = FIXED_NOW) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class FakeHealthRepository(IHealthRepository):
    def __init__(self, reachable: bool) -> None:
        self._reachable = reachable

    async def is_database_reachable(self) -> bool:
        return self._reachable


class InMemoryCaseRepository(ICaseRepository):
    """Keeps cases in a dictionary. Behaves as the database-backed repository does."""

    def __init__(self) -> None:
        self._cases: dict[str, CaseSummary] = {}
        self._events: dict[str, list[AuditEvent]] = {}

    async def save(
        self, snapshot: CaseSnapshot, events: Sequence[AuditEvent], now: datetime
    ) -> None:
        existing = self._cases.get(snapshot.case_id)
        self._cases[snapshot.case_id] = CaseSummary(
            **snapshot.model_dump(),
            created_at=existing.created_at if existing else now,
            updated_at=now,
        )
        recorded = self._events.setdefault(snapshot.case_id, [])
        recorded.extend(events[len(recorded) :])

    async def set_status(self, case_id: str, status: CaseStatus, now: datetime) -> bool:
        existing = self._cases.get(case_id)
        if existing is None:
            return False
        self._cases[case_id] = existing.model_copy(update={"status": status, "updated_at": now})
        return True

    async def get(self, case_id: str) -> CaseSummary | None:
        return self._cases.get(case_id)

    async def list(self, page: int, page_size: int, status: CaseStatus | None) -> CasePage:
        matching = [
            case for case in self._cases.values() if status is None or case.status is status
        ]
        matching.sort(key=lambda case: case.created_at, reverse=True)
        start = (page - 1) * page_size
        return CasePage(
            items=tuple(matching[start : start + page_size]),
            page=page,
            page_size=page_size,
            total=len(matching),
        )

    async def list_events(self, case_id: str, after_sequence: int) -> tuple[CaseEvent, ...]:
        return tuple(
            CaseEvent(sequence=sequence, event=event)
            for sequence, event in enumerate(self._events.get(case_id, []), start=1)
            if sequence > after_sequence
        )
