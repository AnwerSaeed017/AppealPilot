from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

from sqlalchemy import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession


class ISqlFunctionCaller(ABC):
    """Calls the database functions defined in app/sql, by name.

    Repositories use this instead of writing SQL: every query lives in a .sql file.
    """

    @abstractmethod
    async def rows(self, session: AsyncSession, name: str, *args: Any) -> Sequence[RowMapping]:
        """Every row a set-returning function gives for these arguments."""

    @abstractmethod
    async def value(self, session: AsyncSession, name: str, *args: Any) -> Any:
        """The single value a function returns for these arguments."""
