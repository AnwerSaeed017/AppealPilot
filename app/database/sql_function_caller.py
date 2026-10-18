from collections.abc import Sequence
from typing import Any

from sqlalchemy import RowMapping, Select, func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.interfaces.database.sql_function_caller import ISqlFunctionCaller


class SqlFunctionCaller(ISqlFunctionCaller):
    """Builds the call from the function's name and its arguments; writes no SQL text.

    Arguments are always sent as bound parameters, never pasted into the statement.
    """

    async def rows(self, session: AsyncSession, name: str, *args: Any) -> Sequence[RowMapping]:
        statement: Select[Any] = select(literal_column("*")).select_from(getattr(func, name)(*args))
        result = await session.execute(statement)
        rows: Sequence[RowMapping] = result.mappings().all()
        return rows

    async def value(self, session: AsyncSession, name: str, *args: Any) -> Any:
        return await session.scalar(select(getattr(func, name)(*args)))
