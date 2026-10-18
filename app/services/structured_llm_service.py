import json
import logging
import re

from pydantic import BaseModel, ValidationError

from app.clients.llm.errors import LlmError, LlmResponseError
from app.core.exceptions import AgentOutputError, ModelProviderError
from app.interfaces.clients.llm_client import ILlmClient
from app.interfaces.service.structured_llm_service import IStructuredLlmService
from app.schemas.audit_event import AgentResult, LlmCallRecord
from app.schemas.llm import LlmMessage, LlmRequest, ReasoningEffort

logger = logging.getLogger(__name__)

# A reply wrapped in a Markdown code fence, with or without a language tag.
_FENCED = re.compile(r"^```[a-zA-Z]*\s*(.*?)\s*```$", re.DOTALL)


class StructuredLlmService(IStructuredLlmService):
    """Gets output of a required shape from one model, re-asking when it does not parse."""

    def __init__(self, llm: ILlmClient, max_attempts: int) -> None:
        self._llm = llm
        self._max_attempts = max_attempts

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
        schema = json.dumps(output_type.model_json_schema())
        messages = [
            LlmMessage(role="system", content=system),
            LlmMessage(
                role="user",
                content=(
                    f"{user}\n\nReply with one JSON object and nothing else. "
                    f"It must match this JSON schema:\n{schema}"
                ),
            ),
        ]
        input_tokens = output_tokens = 0
        latency_ms = 0.0

        for attempt in range(1, self._max_attempts + 1):
            request = LlmRequest(
                task=task,
                prompt_version=prompt_version,
                messages=tuple(messages),
                max_output_tokens=max_output_tokens,
                json_output=True,
                reasoning_effort=reasoning_effort,
            )
            try:
                response = await self._llm.complete(request)
            except LlmResponseError:
                # The provider gave a reply that cannot be used, for example JSON it could
                # not parse itself. Ask again, saying why; the role order stays as it was.
                logger.warning(
                    "Step %s: unusable reply from the provider on attempt %d", task, attempt
                )
                last = messages[-1]
                messages[-1] = LlmMessage(
                    role=last.role,
                    content=f"{last.content}\n\nYour previous reply could not be read as JSON. "
                    "Reply with one JSON object that matches the schema.",
                )
                continue
            except LlmError as error:
                # Retries for passing failures have already happened inside the client.
                logger.exception("Step %s: the model provider failed", task)
                raise ModelProviderError(
                    f"The model provider failed during the {task} step."
                ) from error
            input_tokens += response.usage.input_tokens
            output_tokens += response.usage.output_tokens
            latency_ms += response.latency_ms
            try:
                output = output_type.model_validate_json(self._json_text(response.text))
            except ValidationError as error:
                logger.warning("Step %s: unusable model output on attempt %d", task, attempt)
                problems = json.dumps(error.errors(include_url=False, include_input=False))
                messages += [
                    LlmMessage(role="assistant", content=response.text),
                    LlmMessage(
                        role="user",
                        content=(
                            f"That reply was not valid: {problems}\n"
                            "Reply again with one JSON object that matches the schema."
                        ),
                    ),
                ]
                continue
            return AgentResult[T](
                output=output,
                llm_call=LlmCallRecord(
                    provider=response.provider,
                    model=response.model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    latency_ms=latency_ms,
                    cached=response.cached,
                    attempts=attempt,
                ),
            )

        raise AgentOutputError(
            f"The {task} step did not return usable output in {self._max_attempts} attempts."
        )

    @staticmethod
    def _json_text(text: str) -> str:
        stripped = text.strip()
        fenced = _FENCED.match(stripped)
        return fenced.group(1) if fenced else stripped
