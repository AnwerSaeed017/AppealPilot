from abc import ABC, abstractmethod

from pydantic import BaseModel

from app.schemas.audit_event import AgentResult
from app.schemas.llm import ReasoningEffort


class IStructuredLlmService(ABC):
    @abstractmethod
    async def complete[T: BaseModel](
        self,
        task: str,
        prompt_version: str,
        system: str,
        user: str,
        output_type: type[T],
        max_output_tokens: int,
        reasoning_effort: ReasoningEffort | None = None,
    ) -> AgentResult[T]:
        """Ask the model for output of the given shape.

        Output that does not parse is sent back to the model with the reason, a limited
        number of times. Raises AgentOutputError when no attempt is usable.
        """
