from typing import Any

from app.clients.llm.http_llm_client import HttpLlmClient
from app.schemas.llm import LlmRequest, LlmUsage


class OllamaLlmClient(HttpLlmClient):
    """A local Ollama server's `/api/chat` endpoint."""

    @property
    def provider(self) -> str:
        return "ollama"

    def _url(self) -> str:
        return f"{self._base_url}/api/chat"

    def _headers(self) -> dict[str, str]:
        return {}

    def _payload(self, request: LlmRequest) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": message.role, "content": message.content} for message in request.messages
            ],
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_output_tokens,
            },
        }
        if request.json_output:
            payload["format"] = "json"
        return payload

    def _parse(self, body: Any) -> tuple[str, LlmUsage, str | None]:
        return (
            self._require_text(body["message"]["content"]),
            LlmUsage(
                input_tokens=body.get("prompt_eval_count", 0),
                output_tokens=body.get("eval_count", 0),
            ),
            body.get("done_reason"),
        )
