"""State persistence against a real PostgreSQL, through the application's own wiring.

Skipped when no PostgreSQL is configured. The address comes from TEST_POSTGRES_URL, or
from DATABASE_URL in env/.env. Each test works in its own throwaway schema and drops it
afterwards, so the application's data is never touched.

The application never creates these tables itself; `alembic upgrade head` does. In a
throwaway schema the tests let the workflow engine create its own layout, and one test
checks that the migrated tables have exactly that layout.
"""

import os
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import psycopg
import pytest
from dependency_injector import providers
from dotenv import dotenv_values
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import sql
from psycopg.rows import dict_row

from app.clients.llm.mock_llm_client import MockLlmClient
from app.constants.database import WORKFLOW_SCHEMA
from app.containers.container import Container
from app.core.settings import Settings
from app.database.checkpoint_types import checkpoint_types
from app.database.postgres_checkpoint_store import PostgresCheckpointStore
from app.schemas.case_status import CaseStatus
from tests.fakes import InMemoryCaseRepository
from tests.unit.test_case_workflow import APPROVE, scripted_replies, side_modifier_case


def postgres_url() -> str | None:
    url = os.environ.get("TEST_POSTGRES_URL") or dotenv_values(Path("env/.env")).get("DATABASE_URL")
    return url if url and url.startswith("postgresql") else None


POSTGRES_URL = postgres_url()
pytestmark = pytest.mark.skipif(POSTGRES_URL is None, reason="no PostgreSQL configured")


def identifier(schema: str) -> sql.Identifier:
    return sql.Identifier(schema)


@pytest.fixture
async def empty_schema() -> AsyncIterator[str]:
    """A schema with no tables, used by one test and removed when it ends."""
    assert POSTGRES_URL is not None
    name = f"workflow_test_{uuid.uuid4().hex[:12]}"
    async with await psycopg.AsyncConnection.connect(POSTGRES_URL, autocommit=True) as connection:
        await connection.execute(sql.SQL("CREATE SCHEMA {}").format(identifier(name)))
    yield name
    async with await psycopg.AsyncConnection.connect(POSTGRES_URL, autocommit=True) as connection:
        await connection.execute(
            sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(identifier(name))
        )


@pytest.fixture
async def schema(empty_schema: str) -> str:
    """A throwaway schema holding the workflow engine's tables, as the engine lays them out."""
    assert POSTGRES_URL is not None
    async with await psycopg.AsyncConnection.connect(
        POSTGRES_URL, autocommit=True, prepare_threshold=0, row_factory=dict_row
    ) as connection:
        await connection.execute(sql.SQL("SET search_path TO {}").format(identifier(empty_schema)))
        await AsyncPostgresSaver(connection).setup()
    return empty_schema


def application(schema: str, replies: dict[str, str]) -> tuple[Container, MockLlmClient]:
    """The application's container, pointed at PostgreSQL and at the test's schema."""
    assert POSTGRES_URL is not None
    container = Container()
    settings = Settings(_env_file=None, database_url=POSTGRES_URL)
    container.settings.override(providers.Object(settings))
    container.checkpoint_store.override(
        providers.Singleton(
            PostgresCheckpointStore,
            dsn=settings.postgres_dsn,
            schema=schema,
            pool_max_size=2,
            state_types=checkpoint_types(),
        )
    )
    mock = MockLlmClient(replies)
    container.clients.mock_llm.override(providers.Object(mock))
    # These tests are about the engine's saved state; the case tables have their own.
    container.repositories.case_repository.override(providers.Object(InMemoryCaseRepository()))
    return container, mock


async def layout(schema: str) -> set[tuple[str, str, str, str]]:
    """Every column of every table in a schema: table, column, type, nullable."""
    assert POSTGRES_URL is not None
    async with await psycopg.AsyncConnection.connect(POSTGRES_URL) as connection:
        cursor = await connection.execute(
            "SELECT table_name, column_name, data_type, is_nullable "
            "FROM information_schema.columns WHERE table_schema = %s",
            (schema,),
        )
        return {(row[0], row[1], row[2], row[3]) for row in await cursor.fetchall()}


async def test_the_saver_is_not_available_before_the_store_is_open(schema: str) -> None:
    container, _ = application(schema, {})

    with pytest.raises(RuntimeError, match="not open"):
        container.checkpointer()


async def test_opening_creates_nothing_and_says_to_run_the_migrations(
    empty_schema: str,
) -> None:
    container, _ = application(empty_schema, {})

    with pytest.raises(RuntimeError, match="alembic upgrade head"):
        await container.checkpoint_store().open()

    assert await layout(empty_schema) == set()


async def test_opening_refuses_a_layout_older_than_the_engine_expects(schema: str) -> None:
    assert POSTGRES_URL is not None
    async with await psycopg.AsyncConnection.connect(POSTGRES_URL, autocommit=True) as connection:
        table = sql.SQL("{}.checkpoint_migrations").format(identifier(schema))
        await connection.execute(
            sql.SQL("DELETE FROM {} WHERE v = (SELECT max(v) FROM {})").format(table, table)
        )
    container, _ = application(schema, {})

    with pytest.raises(RuntimeError, match="layout version"):
        await container.checkpoint_store().open()


async def test_the_migrated_tables_have_the_layout_the_engine_expects(schema: str) -> None:
    """The models in app/models and the installed engine must describe the same tables.

    Compares the schema `alembic upgrade head` creates with one the engine laid out
    itself. A failure after upgrading the engine means: update the models, add a
    migration, and run it.
    """
    migrated = await layout(WORKFLOW_SCHEMA)
    if not migrated:
        pytest.skip('schema "workflow" is empty here; run: alembic upgrade head')

    assert migrated == await layout(schema)


async def test_a_paused_case_survives_a_restart_without_redoing_steps(
    schema: str, caplog: pytest.LogCaptureFixture
) -> None:
    case = side_modifier_case()

    # First process: run a case to the approval gate, then shut down.
    first, first_mock = application(schema, scripted_replies(case))
    await first.checkpoint_store().open()
    paused = await first.agents.case_workflow().start("CASE-1", case.case_input(), case.as_of_date)
    await first.checkpoint_store().close()

    assert paused.status is CaseStatus.AWAITING_APPROVAL
    assert len(first_mock.calls) == 4

    # Second process: the model has no replies, so any repeated step would fail.
    second, second_mock = application(schema, {})
    await second.checkpoint_store().open()
    workflow = second.agents.case_workflow()

    restored = await workflow.get("CASE-1")
    assert restored == paused

    finished = await workflow.resume("CASE-1", APPROVE)
    await second.checkpoint_store().close()

    assert finished.status is CaseStatus.APPROVED
    assert finished.draft == paused.draft
    assert len(finished.audit) == 10
    assert second_mock.calls == ()
    # Every class in the saved state is registered, so none is loaded on sufferance.
    assert "unregistered type" not in caplog.text


async def test_cases_are_kept_apart_by_case_id(schema: str) -> None:
    case = side_modifier_case()
    container, _ = application(schema, scripted_replies(case))
    await container.checkpoint_store().open()
    workflow = container.agents.case_workflow()

    await workflow.start("CASE-A", case.case_input(), case.as_of_date)
    await workflow.start("CASE-B", case.case_input(), case.as_of_date)
    await workflow.resume("CASE-A", APPROVE)
    case_a, case_b = await workflow.get("CASE-A"), await workflow.get("CASE-B")
    await container.checkpoint_store().close()

    assert case_a is not None
    assert case_a.status is CaseStatus.APPROVED
    assert case_b is not None
    assert case_b.status is CaseStatus.AWAITING_APPROVAL
