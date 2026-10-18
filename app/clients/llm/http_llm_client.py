import time
from abc import abstractmethod
from typing import Any

import httpx

from app.clients.llm.errors import (
    LlmRateLimitError,
    LlmRequestError,
    LlmResponseError,
    LlmUnavailableError,
)
from app.constants.llm import ERROR_BODY_LIMIT
from app.interfaces.clients.llm_client import ILlmClient
from app.schemas.llm import LlmRequest, LlmResponse, LlmUsage


class HttpLlmClient(ILlmClient):
    """Shared transport for providers reached over HTTP with a JSON body.

    Subclasses describe the provider's wire format; this class owns the call, the
    timing and the mapping from HTTP failures to `LlmError` types.
    """

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        base_url: str,
        model: str,
        timeout_seconds: float,
    ) -> None:
        self._http_client = http_client
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_seconds = timeout_seconds

    @property
    def model(self) -> str:
        return self._model

    async def complete(self, request: LlmRequest) -> LlmResponse:
        started = time.perf_counter()
        try:
            http_response = await self._http_client.post(
                self._url(),
                headers=self._headers(),
                json=self._payload(request),
                timeout=self._timeout_seconds,
            )
        except httpx.TimeoutException as error:
            raise LlmUnavailableError(
                f"{self.provider} timed out after {self._timeout_seconds}s"
            ) from error
        except httpx.HTTPError as error:
            raise LlmUnavailableError(
                f"{self.provider} request failed: {type(error).__name__}"
            ) from error

        self._raise_for_status(http_response)

        try:
            text, usage, finish_reason = self._parse(http_response.json())
        except (ValueError, KeyError, IndexError, TypeError) as error:
            raise LlmResponseError(f"{self.provider} returned an unexpected body") from error
        if not text:
            raise LlmResponseError(f"{self.provider} returned an empty completion")

        return LlmResponse(
            text=text,
            provider=self.provider,
            model=self._model,
            usage=usage,
            latency_ms=(time.perf_counter() - started) * 1000,
            finish_reason=finish_reason,
        )

    @abstractmethod
    def _url(self) -> str:
        """Full URL of the completion endpoint."""

    @abstractmethod
    def _headers(self) -> dict[str, str]:
        """Request headers, including any credentials."""

    @abstractmethod
    def _payload(self, request: LlmRequest) -> dict[str, Any]:
        """The provider's JSON request body."""

    @abstractmethod
    def _parse(self, body: Any) -> tuple[str, LlmUsage, str | None]:
        """Extract (text, usage, finish reason) from the provider's JSON response.

        May raise KeyError, IndexError, TypeError or ValueError on an unexpected shape.
        """

    def _raise_for_status(self, http_response: httpx.Response) -> None:
        status = http_response.status_code
        if status < 400:
            return
        detail = f"{self.provider} returned HTTP {status}: {http_response.text[:ERROR_BODY_LIMIT]}"
        if status == 429:
            raise LlmRateLimitError(detail, self._retry_after(http_response))
        if status >= 500:
            raise LlmUnavailableError(detail)
        raise LlmRequestError(detail)

    @staticmethod
    def _retry_after(http_response: httpx.Response) -> float | None:
        try:
            return float(http_response.headers["retry-after"])
        except (KeyError, ValueError):
            return None

    @staticmethod
    def _require_text(value: Any) -> str:
        if not isinstance(value, str):
            raise TypeError("completion text is not a string")
        return value
