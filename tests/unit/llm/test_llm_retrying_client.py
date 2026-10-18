import pytest

from app.clients.llm.errors import (
    LlmError,
    LlmRateLimitError,
    LlmRequestError,
    LlmRequestTooLargeError,
    LlmResponseError,
    LlmUnavailableError,
)
from app.clients.llm.retrying_llm_client import RetryingLlmClient
from app.interfaces.clients.llm_client import ILlmClient
from app.schemas.llm import LlmMessage, LlmRequest, LlmResponse, LlmUsage

REQUEST = LlmRequest(
    task="triage", prompt_version="1", messages=(LlmMessage(role="user", content="Decide."),)
)


class FlakyLlmClient(ILlmClient):
    """Raises the given errors in order, then answers."""

    def __init__(self, errors: list[LlmError]) -> None:
        self._errors = list(errors)
        self.calls = 0

    @property
    def provider(self) -> str:
        return "flaky"

    @property
    def model(self) -> str:
        return "flaky-1"

    async def complete(self, request: LlmRequest) -> LlmResponse:
        self.calls += 1
        if self._errors:
            raise self._errors.pop(0)
        return LlmResponse(
            text="ok",
            provider=self.provider,
            model=self.model,
            usage=LlmUsage(input_tokens=1, output_tokens=1),
            latency_ms=1.0,
        )


class Sleeps:
    """Records the waits asked for, and waits for none of them."""

    def __init__(self) -> None:
        self.waits: list[float] = []

    async def __call__(self, seconds: float) -> None:
        self.waits.append(seconds)


def retrying(
    inner: ILlmClient, sleeps: Sleeps, max_retries: int = 3, jitter: float = 1.0
) -> RetryingLlmClient:
    return RetryingLlmClient(
        inner,
        max_retries=max_retries,
        base_delay_seconds=1.0,
        max_delay_seconds=10.0,
        sleep=sleeps,
        jitter=lambda: jitter,
    )


async def test_success_needs_no_waiting() -> None:
    inner, sleeps = FlakyLlmClient([]), Sleeps()

    response = await retrying(inner, sleeps).complete(REQUEST)

    assert response.text == "ok"
    assert (inner.calls, sleeps.waits) == (1, [])


async def test_passing_failures_are_retried_with_a_doubling_wait() -> None:
    inner = FlakyLlmClient([LlmUnavailableError("503")] * 3)
    sleeps = Sleeps()

    response = await retrying(inner, sleeps).complete(REQUEST)

    assert response.text == "ok"
    assert inner.calls == 4
    assert sleeps.waits == [1.0, 2.0, 4.0]


async def test_the_wait_is_capped_and_jittered() -> None:
    inner = FlakyLlmClient([LlmUnavailableError("503")] * 6)
    sleeps = Sleeps()

    await retrying(inner, sleeps, max_retries=6, jitter=0.0).complete(REQUEST)

    # With no jitter each wait is half the backoff; the backoff stops growing at 10.
    assert sleeps.waits == [0.5, 1.0, 2.0, 4.0, 5.0, 5.0]


async def test_the_providers_own_wait_is_used_when_given() -> None:
    inner = FlakyLlmClient([LlmRateLimitError("429", retry_after_seconds=7.0)])
    sleeps = Sleeps()

    await retrying(inner, sleeps).complete(REQUEST)

    assert sleeps.waits == [7.0]


async def test_a_wait_longer_than_the_cap_fails_at_once() -> None:
    inner = FlakyLlmClient([LlmRateLimitError("daily quota", retry_after_seconds=3600.0)])
    sleeps = Sleeps()

    with pytest.raises(LlmRateLimitError, match="daily quota"):
        await retrying(inner, sleeps).complete(REQUEST)

    assert (inner.calls, sleeps.waits) == (1, [])


async def test_it_gives_up_after_the_allowed_retries() -> None:
    inner = FlakyLlmClient([LlmUnavailableError("503")] * 10)
    sleeps = Sleeps()

    with pytest.raises(LlmUnavailableError):
        await retrying(inner, sleeps, max_retries=2).complete(REQUEST)

    assert inner.calls == 3
    assert len(sleeps.waits) == 2


@pytest.mark.parametrize("error", [LlmRequestError("400 bad model"), LlmResponseError("empty")])
async def test_failures_that_would_repeat_are_not_retried(error: LlmError) -> None:
    inner, sleeps = FlakyLlmClient([error]), Sleeps()

    with pytest.raises(type(error)):
        await retrying(inner, sleeps).complete(REQUEST)

    assert (inner.calls, sleeps.waits) == (1, [])


async def test_provider_and_model_are_those_of_the_wrapped_client() -> None:
    client = retrying(FlakyLlmClient([]), Sleeps())

    assert (client.provider, client.model) == ("flaky", "flaky-1")


class AllowanceRecorder(FlakyLlmClient):
    """Like FlakyLlmClient, and remembers the reply allowance of each request."""

    def __init__(self, errors: list[LlmError]) -> None:
        super().__init__(errors)
        self.allowances: list[int] = []

    async def complete(self, request: LlmRequest) -> LlmResponse:
        self.allowances.append(request.max_output_tokens)
        return await super().complete(request)


async def test_a_request_too_large_is_sent_again_with_a_smaller_reply_allowance() -> None:
    inner = AllowanceRecorder([LlmRequestTooLargeError("too large", excess_tokens=1258)])
    request = REQUEST.model_copy(update={"max_output_tokens": 4000})

    response = await retrying(inner, Sleeps()).complete(request)

    assert response.text == "ok"
    assert inner.allowances == [4000, 4000 - 1258 - 100]


async def test_a_request_too_large_is_not_shrunk_below_a_useful_reply() -> None:
    inner = AllowanceRecorder([LlmRequestTooLargeError("too large", excess_tokens=3500)])
    request = REQUEST.model_copy(update={"max_output_tokens": 4000})

    with pytest.raises(LlmRequestTooLargeError):
        await retrying(inner, Sleeps()).complete(request)
    assert inner.allowances == [4000]


async def test_a_request_still_too_large_after_shrinking_is_not_shrunk_again() -> None:
    inner = AllowanceRecorder(
        [
            LlmRequestTooLargeError("too large", excess_tokens=500),
            LlmRequestTooLargeError("too large", excess_tokens=500),
        ]
    )
    request = REQUEST.model_copy(update={"max_output_tokens": 4000})

    with pytest.raises(LlmRequestTooLargeError):
        await retrying(inner, Sleeps()).complete(request)
    assert inner.calls == 2
