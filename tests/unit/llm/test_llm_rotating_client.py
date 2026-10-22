"""Several API keys for one provider: a limited or rejected key gives way to the next."""

import pytest

from app.clients.llm.errors import (
    LlmAuthenticationError,
    LlmRateLimitError,
    LlmUnavailableError,
)
from app.clients.llm.rotating_llm_client import RotatingLlmClient
from app.interfaces.clients.llm_client import ILlmClient
from app.schemas.llm import LlmMessage, LlmRequest, LlmResponse, LlmUsage

REQUEST = LlmRequest(
    task="triage",
    prompt_version="1",
    messages=(LlmMessage(role="user", content="hello"),),
    max_output_tokens=10,
)


class KeyClient(ILlmClient):
    """Stands for one key: answers, or fails the way it is told to."""

    def __init__(self, name: str, failure: Exception | None = None) -> None:
        self.name = name
        self.failure = failure
        self.calls = 0

    @property
    def provider(self) -> str:
        return "groq"

    @property
    def model(self) -> str:
        return "model-x"

    async def complete(self, request: LlmRequest) -> LlmResponse:
        self.calls += 1
        if self.failure is not None:
            raise self.failure
        return LlmResponse(
            text=self.name,
            provider="groq",
            model="model-x",
            usage=LlmUsage(input_tokens=1, output_tokens=1),
            latency_ms=1.0,
        )


async def test_the_first_key_answers_when_it_can() -> None:
    first, second = KeyClient("first"), KeyClient("second")

    response = await RotatingLlmClient([first, second]).complete(REQUEST)

    assert response.text == "first"
    assert second.calls == 0


async def test_a_rate_limited_key_gives_way_to_the_next_at_once() -> None:
    limited = KeyClient("first", LlmRateLimitError("429", retry_after_seconds=600))
    rotating = RotatingLlmClient([limited, KeyClient("second")])

    assert (await rotating.complete(REQUEST)).text == "second"


async def test_a_rejected_key_gives_way_to_the_next() -> None:
    rejected = KeyClient("first", LlmAuthenticationError("401"))

    response = await RotatingLlmClient([rejected, KeyClient("second")]).complete(REQUEST)

    assert response.text == "second"


async def test_calls_stay_on_the_key_that_last_worked() -> None:
    limited = KeyClient("first", LlmRateLimitError("429"))
    working = KeyClient("second")
    rotating = RotatingLlmClient([limited, working])

    await rotating.complete(REQUEST)
    await rotating.complete(REQUEST)

    assert (limited.calls, working.calls) == (1, 2)


async def test_when_every_key_is_limited_the_shortest_wait_is_passed_on() -> None:
    rotating = RotatingLlmClient(
        [
            KeyClient("a", LlmRateLimitError("a", retry_after_seconds=900)),
            KeyClient("b", LlmRateLimitError("b", retry_after_seconds=30)),
            KeyClient("c", LlmRateLimitError("c", retry_after_seconds=None)),
        ]
    )

    with pytest.raises(LlmRateLimitError) as raised:
        await rotating.complete(REQUEST)

    assert raised.value.retry_after_seconds == 30


async def test_when_every_key_is_rejected_the_rejection_is_passed_on() -> None:
    rotating = RotatingLlmClient(
        [
            KeyClient("a", LlmAuthenticationError("401")),
            KeyClient("b", LlmAuthenticationError("403")),
        ]
    )

    with pytest.raises(LlmAuthenticationError):
        await rotating.complete(REQUEST)


async def test_other_failures_are_not_a_reason_to_change_keys() -> None:
    # The provider being down is the same for every key; the retrying client handles it.
    down = KeyClient("first", LlmUnavailableError("503"))
    second = KeyClient("second")

    with pytest.raises(LlmUnavailableError):
        await RotatingLlmClient([down, second]).complete(REQUEST)

    assert second.calls == 0


def test_all_keys_must_be_for_one_provider_and_model() -> None:
    class OtherModel(KeyClient):
        @property
        def model(self) -> str:
            return "model-y"

    with pytest.raises(ValueError, match="one provider and model"):
        RotatingLlmClient([KeyClient("a"), OtherModel("b")])
