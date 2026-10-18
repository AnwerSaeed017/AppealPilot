from abc import ABC, abstractmethod
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver


class ICheckpointStore(ABC):
    """Owns the durable storage that workflow state is saved to after every step."""

    @abstractmethod
    async def open(self) -> None:
        """Connect and create the storage if it does not exist. Call once at start-up."""

    @abstractmethod
    async def close(self) -> None:
        """Release the connections. Call once at shutdown."""

    @property
    @abstractmethod
    def saver(self) -> BaseCheckpointSaver[Any]:
        """The checkpointer the workflow writes through. Only valid while open."""
