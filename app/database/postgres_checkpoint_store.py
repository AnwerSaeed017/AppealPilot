from collections.abc import Sequence
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from psycopg import AsyncConnection, sql
from psycopg.errors import UndefinedTable
from psycopg.rows import DictRow, dict_row
from psycopg_pool import AsyncConnectionPool

from app.interfaces.agents.checkpoint_store import ICheckpointStore


class PostgresCheckpointStore(ICheckpointStore):
    """Workflow state in PostgreSQL, in a schema of its own.

    This class creates nothing. The tables are defined in app/models and created by
    `alembic upgrade head`; opening the store only connects and checks that they are
    there, at the layout version the workflow engine expects.
    """

    def __init__(
        self,
        dsn: str,
        schema: str,
        pool_max_size: int,
        state_types: Sequence[tuple[str, str]],
    ) -> None:
        self._dsn = dsn
        self._schema = schema
        self._pool_max_size = pool_max_size
        # The only classes that may be rebuilt from saved state, as (module, name).
        self._state_types = tuple(state_types)
        self._pool: AsyncConnectionPool[AsyncConnection[DictRow]] | None = None
        self._saver: AsyncPostgresSaver | None = None

    async def open(self) -> None:
        if self._saver is not None:
            return
        pool: AsyncConnectionPool[AsyncConnection[DictRow]] = AsyncConnectionPool(
            self._dsn,
            min_size=1,
            max_size=self._pool_max_size,
            # The engine manages its own transactions and needs dictionary rows.
            kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
            configure=self._use_schema,
            open=False,
        )
        await pool.open(wait=True)
        try:
            await self._check_tables(pool)
        except BaseException:
            await pool.close()
            raise
        self._pool = pool
        self._saver = AsyncPostgresSaver(
            pool, serde=JsonPlusSerializer(allowed_msgpack_modules=self._state_types)
        )

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
        self._pool = None
        self._saver = None

    @property
    def saver(self) -> BaseCheckpointSaver[Any]:
        if self._saver is None:
            raise RuntimeError("The checkpoint store is not open.")
        return self._saver

    async def _use_schema(self, connection: AsyncConnection[DictRow]) -> None:
        """Make every connection of the pool work inside the workflow schema."""
        await connection.execute(
            sql.SQL("SET search_path TO {}").format(sql.Identifier(self._schema))
        )

    async def _check_tables(self, pool: AsyncConnectionPool[AsyncConnection[DictRow]]) -> None:
        """Fail at start-up, with the fix, if the migrations have not been applied."""
        expected = len(AsyncPostgresSaver.MIGRATIONS) - 1
        try:
            async with pool.connection() as connection:
                cursor = await connection.execute(
                    "SELECT max(v) AS version FROM checkpoint_migrations"
                )
                row = await cursor.fetchone()
        except UndefinedTable as error:
            raise RuntimeError(
                f'The workflow tables are missing from schema "{self._schema}". '
                "Run: alembic upgrade head"
            ) from error

        found = row["version"] if row else None
        if found != expected:
            raise RuntimeError(
                f"The workflow tables are at layout version {found}, but the installed "
                f"workflow engine expects {expected}. Update the models in app/models to "
                "match it, add a migration, and run: alembic upgrade head"
            )
