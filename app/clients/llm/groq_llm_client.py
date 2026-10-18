import math
from typing import Any

import httpx

from app.clients.llm.errors import LlmRequestTooLargeError, LlmResponseError
from app.clients.llm.http_llm_client import HttpLlmClient
from app.constants.llm import (
    ERROR_BODY_LIMIT,
    ESTIMATED_CHARACTERS_PER_TOKEN,
    GROQ_INVALID_JSON_CODE,
    GROQ_REQUEST_TOO_LARGE,
    MESSAGE_OVERHEAD_TOKENS,
    MIN_REPLY_ALLOWANCE_TOKENS,
)
from app.schemas.llm import LlmRequest, LlmUsage


class GroqLlmClient(HttpLlmClient):
    """Groq's OpenAI-compatible chat completions endpoint.

    With `request_token_limit` set, each reply allowance is cut so that the estimated
    prompt plus the allowance stays within it: Groq refuses a single request bigger than
    the account's per-minute token limit, whatever the account has used.
    """

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: float,
        request_token_limit: int | None = None,
    ) -> None:
        super().__init__(http_client, base_url, model, timeout_seconds)
        self._api_key = api_key
        self._request_token_limit = request_token_limit

    @property
    def provider(self) -> str:
        return "groq"

    def _raise_for_status(self, http_response: httpx.Response) -> None:
        # In JSON mode Groq checks the model's reply itself and answers 400 when it is not
        # valid JSON. The request was fine; the reply was unusable, which callers may retry.
        if http_response.status_code == 400 and GROQ_INVALID_JSON_CODE in http_response.text:
            raise LlmResponseError(f"{self.provider} could not produce valid JSON")
        # Groq counts the prompt plus the reply allowance against its per-minute token
        # limit, and refuses with 413 a single request bigger than that limit. It says by
        # how much, so a caller can ask again with a smaller reply allowance.
        if http_response.status_code == 413:
            match = GROQ_REQUEST_TOO_LARGE.search(http_response.text)
            if match is not None:
                limit, requested = (int(value) for value in match.groups())
                raise LlmRequestTooLargeError(
                    f"{self.provider} returned HTTP 413: {http_response.text[:ERROR_BODY_LIMIT]}",
                    excess_tokens=requested - limit,
                )
        super()._raise_for_status(http_response)

    def _url(self) -> str:
        return f"{self._base_url}/chat/completions"

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}"}

    def _payload(self, request: LlmRequest) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": message.role, "content": message.content} for message in request.messages
            ],
            "temperature": request.temperature,
            "max_completion_tokens": self._reply_allowance(request),
        }
        if request.json_output:
            payload["response_format"] = {"type": "json_object"}
        if request.reasoning_effort is not None:
            payload["reasoning_effort"] = request.reasoning_effort
        return payload

    def _reply_allowance(self, request: LlmRequest) -> int:
        if self._request_token_limit is None:
            return request.max_output_tokens
        characters = sum(len(message.content) for message in request.messages)
        prompt_tokens = math.ceil(characters / ESTIMATED_CHARACTERS_PER_TOKEN)
        room = self._request_token_limit - prompt_tokens - MESSAGE_OVERHEAD_TOKENS
        # Never below a useful reply: if the prompt alone is too big, Groq says so.
        return min(request.max_output_tokens, max(room, MIN_REPLY_ALLOWANCE_TOKENS))

    def _parse(self, body: Any) -> tuple[str, LlmUsage, str | None]:
        choice = body["choices"][0]
        usage = body.get("usage") or {}
        return (
            self._require_text(choice["message"]["content"]),
            LlmUsage(
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
            ),
            choice.get("finish_reason"),
        )
