"""Errors raised by LLM clients. Callers decide whether to retry; clients never do."""


class LlmError(Exception):
    """Base class for every LLM client failure."""


class LlmRateLimitError(LlmError):
    """The provider refused the call because a quota or rate limit was hit."""

    def __init__(self, message: str, retry_after_seconds: float | None = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class LlmUnavailableError(LlmError):
    """Timeout, connection failure or provider-side error. Safe to retry."""


class LlmRequestError(LlmError):
    """The provider rejected the request itself. Retrying unchanged will not help."""


class LlmAuthenticationError(LlmRequestError):
    """The provider rejected the credentials: the key is wrong, revoked or not allowed."""


class LlmRequestTooLargeError(LlmRequestError):
    """The prompt plus the reply allowance is more than the provider takes in one call.

    `excess_tokens` is how much over the limit the request was, as the provider reported
    it. A request with a reply allowance that much smaller would fit.
    """

    def __init__(self, message: str, excess_tokens: int) -> None:
        super().__init__(message)
        self.excess_tokens = excess_tokens


class LlmResponseError(LlmError):
    """The provider answered, but not with a usable completion."""
