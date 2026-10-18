from abc import ABC, abstractmethod
from collections.abc import Coroutine
from typing import Any


class ITaskRunner(ABC):
    """Runs work in the background of this process, after a request has been answered."""

    @abstractmethod
    def start(self, work: Coroutine[Any, Any, None]) -> None:
        """Begin the work and return at once."""

    @abstractmethod
    async def drain(self) -> None:
        """Wait until everything started so far has finished."""

    @abstractmethod
    async def cancel_all(self) -> None:
        """Stop everything still running. Call at shutdown."""
