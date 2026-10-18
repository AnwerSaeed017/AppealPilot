from abc import ABC, abstractmethod

from app.schemas.llm import LlmResponse


class ILlmCache(ABC):
    """Stores completions under an opaque key."""

    @abstractmethod
    async def get(self, key: str) -> LlmResponse | None:
        """Return the stored response, or None when there is no usable entry."""

    @abstractmethod
    async def set(self, key: str, response: LlmResponse) -> None:
        """Store the response, replacing any existing entry."""
