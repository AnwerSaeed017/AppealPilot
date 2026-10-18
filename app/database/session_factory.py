from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from sqlalchemy.ext.asyncio import AsyncSession

# What a repository receives: call it to open one unit of work.
SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]
