import json
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import RowMapping

from app.constants.sql_functions import (
    CASE_COUNT,
    CASE_EVENTS_LIST,
    CASE_GET,
    CASE_LIST,
    CASE_SAVE,
    CASE_SET_STATUS,
)
from app.database.session_factory import SessionFactory
from app.interfaces.database.sql_function_caller import ISqlFunctionCaller
from app.interfaces.repository.case_repository import ICaseRepository
from app.schemas.audit_event import AuditEvent, LlmCallRecord
from app.schemas.case_status import CaseStatus
from app.schemas.case_summary import CaseEvent, CasePage, CaseSnapshot, CaseSummary
from app.schemas.recommended_action import RecommendedAction


class CaseRepository(ICaseRepository):
    """The case tables, reached only through the functions in app/sql/functions/cases."""

    def __init__(self, session_factory: SessionFactory, sql: ISqlFunctionCaller) -> None:
        self._session_factory = session_factory
        self._sql = sql

    async def save(
        self, snapshot: CaseSnapshot, events: Sequence[AuditEvent], now: datetime
    ) -> None:
        trail = json.dumps([event.model_dump(mode="json") for event in events])
        async with self._session_factory() as session:
            await self._sql.value(
                session,
                CASE_SAVE,
                snapshot.case_id,
                snapshot.claim_id,
                snapshot.payer_id,
                snapshot.carc_code,
                snapshot.as_of,
                snapshot.status.value,
                snapshot.action.value if snapshot.action else None,
                snapshot.verified,
                now,
                trail,
            )

    async def set_status(self, case_id: str, status: CaseStatus, now: datetime) -> bool:
        async with self._session_factory() as session:
            return bool(await self._sql.value(session, CASE_SET_STATUS, case_id, status.value, now))

    async def get(self, case_id: str) -> CaseSummary | None:
        async with self._session_factory() as session:
            rows = await self._sql.rows(session, CASE_GET, case_id)
        return self._summary(rows[0]) if rows else None

    async def list(self, page: int, page_size: int, status: CaseStatus | None) -> CasePage:
        status_value = status.value if status else None
        async with self._session_factory() as session:
            rows = await self._sql.rows(
                session, CASE_LIST, status_value, page_size, (page - 1) * page_size
            )
            total = await self._sql.value(session, CASE_COUNT, status_value)
        return CasePage(
            items=tuple(self._summary(row) for row in rows),
            page=page,
            page_size=page_size,
            total=int(total or 0),
        )

    async def list_events(self, case_id: str, after_sequence: int) -> tuple[CaseEvent, ...]:
        async with self._session_factory() as session:
            rows = await self._sql.rows(session, CASE_EVENTS_LIST, case_id, after_sequence)
        return tuple(self._event(row) for row in rows)

    @staticmethod
    def _summary(row: RowMapping) -> CaseSummary:
        return CaseSummary(
            case_id=row["id"],
            claim_id=row["claim_id"],
            payer_id=row["payer_id"],
            carc_code=row["carc_code"],
            as_of=row["as_of"],
            status=CaseStatus(row["status"]),
            action=RecommendedAction(row["action"]) if row["action"] else None,
            verified=row["verified"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _event(row: RowMapping) -> CaseEvent:
        call = None
        if row["provider"] is not None and row["model"] is not None:
            call = LlmCallRecord(
                provider=row["provider"],
                model=row["model"],
                input_tokens=row["input_tokens"] or 0,
                output_tokens=row["output_tokens"] or 0,
                latency_ms=row["latency_ms"] or 0.0,
                cached=bool(row["cached"]),
                attempts=row["attempts"] or 1,
            )
        return CaseEvent(
            sequence=row["sequence"],
            event=AuditEvent(step=row["step"], at=row["at"], summary=row["summary"], llm_call=call),
        )
