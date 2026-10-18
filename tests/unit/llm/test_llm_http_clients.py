import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from app.clients.llm.errors import (
    LlmRateLimitError,
    LlmRequestError,
    LlmRequestTooLargeError,
    LlmResponseError,
    LlmUnavailableError,
)
from app.clients.llm.gemini_llm_client import GeminiLlmClient
from app.clients.llm.groq_llm_client import GroqLlmClient
from app.clients.llm.ollama_llm_client import OllamaLlmClient
from app.interfaces.clients.llm_client import ILlmClient
from app.schemas.llm import LlmMessage, LlmRequest

Handler = Callable[[httpx.Request], httpx.Response]

REQUEST = LlmRequest(
    task="triage",
    prompt_version="1",
    messages=(
        LlmMessage(role="system", content="You are careful."),
        LlmMessage(role="user", content="Decide."),
    ),
    max_output_tokens=256,
    json_output=True,
)

GROQ_BODY = {
    "choices": [{"message": {"content": '{"ok": true}'}, "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 42, "completion_tokens": 7},
}
GEMINI_BODY = {
    "candidates": [
        {"content": {"parts": [{"text": '{"ok": '}, {"text": "true}"}]}, "finishReason": "STOP"}
    ],
    "usageMetadata": {"promptTokenCount": 42, "candidatesTokenCount": 7},
}
OLLAMA_BODY = {
    "message": {"content": '{"ok": true}'},
    "prompt_eval_count": 42,
    "eval_count": 7,
    "done_reason": "stop",
}


def http_client(handler: Handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def groq(handler: Handler) -> GroqLlmClient:
    return GroqLlmClient(http_client(handler), "key-123", "https://groq.test/v1/", "model-g", 5.0)


def gemini(handler: Handler) -> GeminiLlmClient:
    return GeminiLlmClient(
        http_client(handler), "key-456", "https://gemini.test/v1", "model-m", 5.0
    )


def ollama(handler: Handler) -> OllamaLlmClient:
    return OllamaLlmClient(http_client(handler), "http://ollama.test", "model-o", 5.0)


def capture(body: dict[str, Any]) -> tuple[list[httpx.Request], Handler]:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=body)

    return seen, handler


async def test_groq_request_and_response() -> None:
    seen, handler = capture(GROQ_BODY)

    response = await groq(handler).complete(REQUEST)

    sent = json.loads(seen[0].content)
    assert str(seen[0].url) == "https://groq.test/v1/chat/completions"
    assert seen[0].headers["authorization"] == "Bearer key-123"
    assert sent["model"] == "model-g"
    assert sent["messages"][0] == {"role": "system", "content": "You are careful."}
    assert sent["temperature"] == 0.0
    assert sent["max_completion_tokens"] == 256
    assert sent["response_format"] == {"type": "json_object"}
    assert response.text == '{"ok": true}'
    assert (response.provider, response.model) == ("groq", "model-g")
    assert (response.usage.input_tokens, response.usage.output_tokens) == (42, 7)
    assert response.finish_reason == "stop"
    assert response.cached is False


async def test_gemini_request_and_response() -> None:
    seen, handler = capture(GEMINI_BODY)

    response = await gemini(handler).complete(REQUEST)

    sent = json.loads(seen[0].content)
    assert str(seen[0].url) == "https://gemini.test/v1/models/model-m:generateContent"
    assert seen[0].headers["x-goog-api-key"] == "key-456"
    assert "key-456" not in str(seen[0].url)
    assert sent["systemInstruction"] == {"parts": [{"text": "You are careful."}]}
    assert sent["contents"] == [{"role": "user", "parts": [{"text": "Decide."}]}]
    assert sent["generationConfig"] == {
        "temperature": 0.0,
        "maxOutputTokens": 256,
        "responseMimeType": "application/json",
    }
    assert response.text == '{"ok": true}'
    assert (response.usage.input_tokens, response.usage.output_tokens) == (42, 7)
    assert response.finish_reason == "STOP"


async def test_gemini_maps_assistant_turns_to_the_model_role() -> None:
    seen, handler = capture(GEMINI_BODY)
    request = LlmRequest(
        task="writer",
        prompt_version="1",
        messages=(
            LlmMessage(role="user", content="Draft."),
            LlmMessage(role="assistant", content="Draft one."),
            LlmMessage(role="user", content="Fix sentence 2."),
        ),
    )

    await gemini(handler).complete(request)

    sent = json.loads(seen[0].content)
    assert [turn["role"] for turn in sent["contents"]] == ["user", "model", "user"]
    assert "systemInstruction" not in sent
    assert "responseMimeType" not in sent["generationConfig"]


async def test_ollama_request_and_response() -> None:
    seen, handler = capture(OLLAMA_BODY)

    response = await ollama(handler).complete(REQUEST)

    sent = json.loads(seen[0].content)
    assert str(seen[0].url) == "http://ollama.test/api/chat"
    assert sent["stream"] is False
    assert sent["format"] == "json"
    assert sent["options"] == {"temperature": 0.0, "num_predict": 256}
    assert response.text == '{"ok": true}'
    assert (response.usage.input_tokens, response.usage.output_tokens) == (42, 7)


CLIENTS: list[Callable[[Handler], ILlmClient]] = [groq, gemini, ollama]


@pytest.mark.parametrize("build", CLIENTS)
async def test_rate_limit_carries_retry_after(build: Callable[[Handler], ILlmClient]) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"retry-after": "12"}, text="slow down")

    with pytest.raises(LlmRateLimitError) as raised:
        await build(handler).complete(REQUEST)

    assert raised.value.retry_after_seconds == 12.0


@pytest.mark.parametrize("build", CLIENTS)
async def test_server_error_is_retryable(build: Callable[[Handler], ILlmClient]) -> None:
    with pytest.raises(LlmUnavailableError, match="HTTP 503"):
        await build(lambda _: httpx.Response(503, text="overloaded")).complete(REQUEST)


@pytest.mark.parametrize("build", CLIENTS)
async def test_client_error_is_not_retryable(build: Callable[[Handler], ILlmClient]) -> None:
    with pytest.raises(LlmRequestError, match="HTTP 400"):
        await build(lambda _: httpx.Response(400, text="bad model")).complete(REQUEST)


@pytest.mark.parametrize("build", CLIENTS)
async def test_timeout_is_retryable(build: Callable[[Handler], ILlmClient]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("too slow", request=request)

    with pytest.raises(LlmUnavailableError, match="timed out"):
        await build(handler).complete(REQUEST)


@pytest.mark.parametrize("build", CLIENTS)
async def test_connection_failure_is_retryable(build: Callable[[Handler], ILlmClient]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(LlmUnavailableError, match="ConnectError"):
        await build(handler).complete(REQUEST)


@pytest.mark.parametrize("build", CLIENTS)
@pytest.mark.parametrize("body", [{}, {"choices": []}, {"candidates": []}, {"message": {}}, []])
async def test_unexpected_body_is_a_response_error(
    build: Callable[[Handler], ILlmClient], body: Any
) -> None:
    with pytest.raises(LlmResponseError):
        await build(lambda _: httpx.Response(200, json=body)).complete(REQUEST)


@pytest.mark.parametrize("build", CLIENTS)
async def test_non_json_body_is_a_response_error(build: Callable[[Handler], ILlmClient]) -> None:
    with pytest.raises(LlmResponseError):
        await build(lambda _: httpx.Response(200, text="<html>gateway</html>")).complete(REQUEST)


async def test_empty_completion_is_a_response_error() -> None:
    body = {"choices": [{"message": {"content": ""}}]}

    with pytest.raises(LlmResponseError, match="empty completion"):
        await groq(lambda _: httpx.Response(200, json=body)).complete(REQUEST)


async def test_null_content_is_a_response_error() -> None:
    body = {"choices": [{"message": {"content": None}}]}

    with pytest.raises(LlmResponseError):
        await groq(lambda _: httpx.Response(200, json=body)).complete(REQUEST)


async def test_api_key_is_not_in_error_messages() -> None:
    with pytest.raises(LlmRequestError) as raised:
        await groq(lambda _: httpx.Response(401, text="invalid key")).complete(REQUEST)

    assert "key-123" not in str(raised.value)


async def test_groq_rejecting_its_own_reply_as_invalid_json_is_an_unusable_reply() -> None:
    body = {"error": {"message": "Failed to generate JSON.", "code": "json_validate_failed"}}

    with pytest.raises(LlmResponseError, match="valid JSON"):
        await groq(lambda _: httpx.Response(400, json=body)).complete(REQUEST)


async def test_groq_request_over_its_token_limit_reports_the_excess() -> None:
    body = {
        "error": {
            "message": "Request too large for model `openai/gpt-oss-120b` on tokens per "
            "minute (TPM): Limit 8000, Requested 9258, please reduce your message size."
        }
    }

    with pytest.raises(LlmRequestTooLargeError) as raised:
        await groq(lambda _: httpx.Response(413, json=body)).complete(REQUEST)

    assert raised.value.excess_tokens == 1258


async def test_groq_413_without_the_numbers_is_a_plain_request_error() -> None:
    with pytest.raises(LlmRequestError) as raised:
        await groq(lambda _: httpx.Response(413, text="too large")).complete(REQUEST)

    assert not isinstance(raised.value, LlmRequestTooLargeError)


def budgeted_groq(handler: Handler, limit: int) -> GroqLlmClient:
    return GroqLlmClient(
        http_client(handler), "key-123", "https://groq.test/v1/", "model-g", 5.0, limit
    )


def prompt_of(characters: int, allowance: int) -> LlmRequest:
    return LlmRequest(
        task="writer",
        prompt_version="1",
        messages=(LlmMessage(role="user", content="x" * characters),),
        max_output_tokens=allowance,
    )


async def test_groq_reply_allowance_is_cut_to_fit_the_request_token_limit() -> None:
    seen, handler = capture(GROQ_BODY)

    # 18,500 characters is about 5,000 tokens: with 150 for overhead, 2,850 remain of 8,000.
    await budgeted_groq(handler, 8000).complete(prompt_of(18_500, 4000))

    allowance = json.loads(seen[0].content)["max_completion_tokens"]
    assert 2700 <= allowance <= 2900


async def test_groq_reply_allowance_is_kept_when_it_already_fits() -> None:
    seen, handler = capture(GROQ_BODY)

    await budgeted_groq(handler, 8000).complete(prompt_of(2_000, 1500))

    assert json.loads(seen[0].content)["max_completion_tokens"] == 1500


async def test_groq_reply_allowance_never_drops_below_a_useful_reply() -> None:
    seen, handler = capture(GROQ_BODY)

    await budgeted_groq(handler, 8000).complete(prompt_of(40_000, 4000))

    assert json.loads(seen[0].content)["max_completion_tokens"] == 1000


async def test_groq_without_a_token_limit_sends_the_allowance_asked_for() -> None:
    seen, handler = capture(GROQ_BODY)

    await groq(handler).complete(prompt_of(18_500, 4000))

    assert json.loads(seen[0].content)["max_completion_tokens"] == 4000


async def test_groq_sends_reasoning_effort_only_when_asked() -> None:
    seen, handler = capture(GROQ_BODY)
    client = groq(handler)

    await client.complete(REQUEST.model_copy(update={"reasoning_effort": "low"}))
    await client.complete(REQUEST)

    assert json.loads(seen[0].content)["reasoning_effort"] == "low"
    assert "reasoning_effort" not in json.loads(seen[1].content)
