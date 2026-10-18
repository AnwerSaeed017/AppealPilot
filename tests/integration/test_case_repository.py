"""The case repository against a real PostgreSQL.

Skipped when no PostgreSQL is configured. These tests write to the real `cases` tables,
under case IDs made up for the test, and delete exactly those rows afterwards.
"""

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta

import psycopg
import pytest
from dependency_injector import providers

from app.containers.container import Container
from app.core.settings import Settings
from app.interfaces.repository.case_repository import ICaseRepository
from app.schemas.audit_event import AuditEvent, LlmCallRecord
from app.schemas.case_status import CaseStatus
from app.schemas.case_summary import CaseSnapshot
from app.schemas.recommended_action import RecommendedAction
from tests.integration.test_postgres_checkpoint_store import POSTGRES_URL

pytestmark = pytest.mark.skipif(POSTGRES_URL is None, reason="no PostgreSQL configured")

T0 = datetime(2026, 10, 12, 9, 0, tzinfo=UTC)
CALL = LlmCallRecord(
    provider="groq",
    model="some-model",
    input_tokens=900,
    output_tokens=120,
    latency_ms=812.5,
    cached=False,
    attempts=2,
)


def event(step: str, llm_call: LlmCallRecord | None = None) -> AuditEvent:
    return AuditEvent(step=step, at=T0, summary=f"The {step} step ran.", llm_call=llm_call)


def snapshot(
    case_id: str, status: CaseStatus = CaseStatus.RUNNING, **changes: object
) -> CaseSnapshot:
    return CaseSnapshot(
        case_id=case_id,
        claim_id="CLM-TEST",
        payer_id="TESS",
        carc_code="4",
        as_of=date(2026, 10, 12),
        status=status,
        **changes,
    )


@pytest.fixture
async def repository() -> AsyncIterator[ICaseRepository]:
    assert POSTGRES_URL is not None
    container = Container()
    container.settings.override(
        providers.Object(Settings(_env_file=None, database_url=POSTGRES_URL))
    )
    yield container.repositories.case_repository()
    await container.database().dispose()


@pytest.fixture
async def case_ids() -> AsyncIterator[list[str]]:
    """Three fresh case IDs; whatever the test stored under them is removed afterwards."""
    assert POSTGRES_URL is not None
    ids = [str(uuid.uuid4()) for _ in range(3)]
    yield ids
    async with await psycopg.AsyncConnection.connect(POSTGRES_URL, autocommit=True) as connection:
        await connection.execute("DELETE FROM cases WHERE id = ANY(%s)", (ids,))


async def test_an_unknown_case(repository: ICaseRepository, case_ids: list[str]) -> None:
    assert await repository.get(case_ids[0]) is None
    assert await repository.list_events(case_ids[0], 0) == ()
    assert await repository.set_status(case_ids[0], CaseStatus.FAILED, T0) is False


async def test_saving_creates_the_case_and_its_steps(
    repository: ICaseRepository, case_ids: list[str]
) -> None:
    case_id = case_ids[0]

    await repository.save(snapshot(case_id), [event("rules"), event("intake", CALL)], T0)

    summary = await repository.get(case_id)
    assert summary is not None
    assert (summary.status, summary.action, summary.verified) == (CaseStatus.RUNNING, None, None)
    assert (summary.created_at, summary.updated_at) == (T0, T0)
    events = await repository.list_events(case_id, 0)
    assert [(item.sequence, item.event.step) for item in events] == [(1, "rules"), (2, "intake")]
    assert events[0].event.llm_call is None
    assert events[1].event.llm_call == CALL


async def test_saving_again_updates_the_case_and_adds_only_new_steps(
    repository: ICaseRepository, case_ids: list[str]
) -> None:
    case_id = case_ids[0]
    later = T0 + timedelta(minutes=5)
    await repository.save(snapshot(case_id), [event("rules")], T0)

    progressed = snapshot(
        case_id,
        CaseStatus.AWAITING_APPROVAL,
        action=RecommendedAction.NO_ACTION,
        verified=True,
    )
    for _ in range(2):  # the second save is a repeat and must change nothing
        await repository.save(progressed, [event("rules"), event("triage")], later)

    summary = await repository.get(case_id)
    assert summary is not None
    assert summary.status is CaseStatus.AWAITING_APPROVAL
    assert summary.action is RecommendedAction.NO_ACTION
    assert summary.verified is True
    assert (summary.created_at, summary.updated_at) == (T0, later)
    assert [item.event.step for item in await repository.list_events(case_id, 0)] == [
        "rules",
        "triage",
    ]


async def test_steps_can_be_read_from_a_position(
    repository: ICaseRepository, case_ids: list[str]
) -> None:
    case_id = case_ids[0]
    await repository.save(
        snapshot(case_id), [event("rules"), event("retrieval"), event("intake")], T0
    )

    assert [item.sequence for item in await repository.list_events(case_id, 1)] == [2, 3]
    assert await repository.list_events(case_id, 3) == ()


async def test_status_can_be_set_directly(repository: ICaseRepository, case_ids: list[str]) -> None:
    case_id = case_ids[0]
    later = T0 + timedelta(minutes=1)
    await repository.save(snapshot(case_id), [], T0)

    assert await repository.set_status(case_id, CaseStatus.FAILED, later) is True

    summary = await repository.get(case_id)
    assert summary is not None
    assert (summary.status, summary.updated_at) == (CaseStatus.FAILED, later)


async def test_listing_is_newest_first_filtered_and_paged(
    repository: ICaseRepository, case_ids: list[str]
) -> None:
    # Dated in the future, so these three sort ahead of anything else in the table.
    base = datetime(2099, 1, 1, tzinfo=UTC)
    oldest, middle, newest = case_ids
    await repository.save(snapshot(oldest, CaseStatus.FAILED), [], base)
    await repository.save(snapshot(middle), [], base + timedelta(hours=1))
    await repository.save(snapshot(newest, CaseStatus.FAILED), [], base + timedelta(hours=2))

    first_page = await repository.list(page=1, page_size=2, status=None)
    failed = await repository.list(page=1, page_size=10, status=CaseStatus.FAILED)
    second_failed = await repository.list(page=2, page_size=1, status=CaseStatus.FAILED)

    assert [item.case_id for item in first_page.items] == [newest, middle]
    assert first_page.total >= 3
    assert [item.case_id for item in failed.items][:2] == [newest, oldest]
    assert [item.case_id for item in second_failed.items] == [oldest]
    assert second_failed.total == failed.total


async def test_deleting_a_case_removes_its_steps(
    repository: ICaseRepository, case_ids: list[str]
) -> None:
    assert POSTGRES_URL is not None
    case_id = case_ids[0]
    await repository.save(snapshot(case_id), [event("rules")], T0)

    async with await psycopg.AsyncConnection.connect(POSTGRES_URL, autocommit=True) as connection:
        await connection.execute("DELETE FROM cases WHERE id = %s", (case_id,))

    assert await repository.list_events(case_id, 0) == ()
