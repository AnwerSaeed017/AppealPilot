from typing import Any

import httpx

from app.clients.llm.http_llm_client import HttpLlmClient
from app.schemas.llm import LlmRequest, LlmUsage


class GeminiLlmClient(HttpLlmClient):
    """Google's Gemini `generateContent` endpoint."""

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: float,
    ) -> None:
        super().__init__(http_client, base_url, model, timeout_seconds)
        self._api_key = api_key

    @property
    def provider(self) -> str:
        return "gemini"

    def _url(self) -> str:
        return f"{self._base_url}/models/{self._model}:generateContent"

    def _headers(self) -> dict[str, str]:
        return {"x-goog-api-key": self._api_key}

    def _payload(self, request: LlmRequest) -> dict[str, Any]:
        system_texts = [m.content for m in request.messages if m.role == "system"]
        generation_config: dict[str, Any] = {
            "temperature": request.temperature,
            "maxOutputTokens": request.max_output_tokens,
        }
        if request.json_output:
            generation_config["responseMimeType"] = "application/json"

        payload: dict[str, Any] = {
            "contents": [
                {
                    "role": "model" if message.role == "assistant" else "user",
                    "parts": [{"text": message.content}],
                }
                for message in request.messages
                if message.role != "system"
            ],
            "generationConfig": generation_config,
        }
        if system_texts:
            payload["systemInstruction"] = {"parts": [{"text": "\n\n".join(system_texts)}]}
        return payload

    def _parse(self, body: Any) -> tuple[str, LlmUsage, str | None]:
        candidate = body["candidates"][0]
        text = "".join(self._require_text(part["text"]) for part in candidate["content"]["parts"])
        usage = body.get("usageMetadata") or {}
        return (
            text,
            LlmUsage(
                input_tokens=usage.get("promptTokenCount", 0),
                output_tokens=usage.get("candidatesTokenCount", 0),
            ),
            candidate.get("finishReason"),
        )
