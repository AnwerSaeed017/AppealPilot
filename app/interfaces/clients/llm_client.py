from abc import ABC, abstractmethod

from app.schemas.llm import LlmRequest, LlmResponse


class ILlmClient(ABC):
    """A chat-completion client bound to one provider and one model."""

    @property
    @abstractmethod
    def provider(self) -> str:
        """Stable provider name, for example "groq"."""

    @property
    @abstractmethod
    def model(self) -> str:
        """The exact model identifier this client calls."""

    @abstractmethod
    async def complete(self, request: LlmRequest) -> LlmResponse:
        """Return one completion, or raise an `LlmError`."""
