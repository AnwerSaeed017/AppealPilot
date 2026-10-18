import asyncio
import logging
import random
from collections.abc import Awaitable, Callable

from app.clients.llm.errors import (
    LlmRateLimitError,
    LlmRequestTooLargeError,
    LlmUnavailableError,
)
from app.constants.llm import MIN_REPLY_ALLOWANCE_TOKENS, REPLY_ALLOWANCE_MARGIN_TOKENS
from app.interfaces.clients.llm_client import ILlmClient
from app.schemas.llm import LlmRequest, LlmResponse

logger = logging.getLogger(__name__)


class RetryingLlmClient(ILlmClient):
    """Wraps another client and retries calls that failed for a passing reason.

    Retried: rate limits, timeouts, connection failures and provider-side errors.
    Never retried: a request the provider rejected, or a reply that was not a usable
    completion, since asking again unchanged would fail the same way.

    The wait doubles with each attempt, with random jitter so that several callers do
    not retry in step. When the provider says how long to wait, that is used instead.
    If that wait is longer than `max_delay_seconds` (a daily quota, say), the error is
    raised at once: waiting would not help within any reasonable time.

    A request too large for the provider's per-call limit is sent once more with its
    reply allowance reduced by the excess the provider reported, if what is left is
    still a useful allowance. That is not a retry of the same request: it changes the one
    thing that made it too large.
    """

    def __init__(
        self,
        inner: ILlmClient,
        max_retries: int,
        base_delay_seconds: float,
        max_delay_seconds: float,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        jitter: Callable[[], float] = random.random,
    ) -> None:
        self._inner = inner
        self._max_retries = max_retries
        self._base_delay_seconds = base_delay_seconds
        self._max_delay_seconds = max_delay_seconds
        self._sleep = sleep
        self._jitter = jitter

    @property
    def provider(self) -> str:
        return self._inner.provider

    @property
    def model(self) -> str:
        return self._inner.model

    async def complete(self, request: LlmRequest) -> LlmResponse:
        try:
            return await self._complete_with_retries(request)
        except LlmRequestTooLargeError as error:
            allowance = (
                request.max_output_tokens - error.excess_tokens - REPLY_ALLOWANCE_MARGIN_TOKENS
            )
            if allowance < MIN_REPLY_ALLOWANCE_TOKENS:
                raise
            logger.warning(
                "%s call for task %s is %d tokens over the provider's limit; "
                "asking again with a reply allowance of %d",
                self.provider,
                request.task,
                error.excess_tokens,
                allowance,
            )
            return await self._complete_with_retries(
                request.model_copy(update={"max_output_tokens": allowance})
            )

    async def _complete_with_retries(self, request: LlmRequest) -> LlmResponse:
        for attempt in range(self._max_retries + 1):
            try:
                return await self._inner.complete(request)
            except (LlmRateLimitError, LlmUnavailableError) as error:
                delay = self._delay(error, attempt)
                if attempt == self._max_retries or delay is None:
                    raise
                logger.warning(
                    "%s call for task %s failed (%s); retry %d of %d in %.1f s",
                    self.provider,
                    request.task,
                    type(error).__name__,
                    attempt + 1,
                    self._max_retries,
                    delay,
                )
                await self._sleep(delay)
        raise AssertionError("unreachable: the loop returns or raises")

    def _delay(self, error: Exception, attempt: int) -> float | None:
        """Seconds to wait before the next attempt, or None when waiting is pointless."""
        if isinstance(error, LlmRateLimitError) and error.retry_after_seconds is not None:
            requested = error.retry_after_seconds
            return requested if requested <= self._max_delay_seconds else None
        backoff = min(self._base_delay_seconds * 2.0**attempt, self._max_delay_seconds)
        # Between half and all of the backoff.
        return backoff * (0.5 + self._jitter() / 2)
