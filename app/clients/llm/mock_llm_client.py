from collections import deque
from collections.abc import Mapping

from app.clients.llm.errors import LlmRequestError
from app.constants.llm import MOCK_MAX_RECORDED_CALLS
from app.interfaces.clients.llm_client import ILlmClient
from app.schemas.llm import LlmRequest, LlmResponse, LlmUsage


class MockLlmClient(ILlmClient):
    """Returns a fixed text per task. For tests, CI and offline development."""

    def __init__(self, responses: Mapping[str, str] | None = None) -> None:
        self._responses = dict(responses or {})
        self._calls: deque[LlmRequest] = deque(maxlen=MOCK_MAX_RECORDED_CALLS)

    @property
    def provider(self) -> str:
        return "mock"

    @property
    def model(self) -> str:
        return "mock"

    @property
    def calls(self) -> tuple[LlmRequest, ...]:
        """The most recent requests, oldest first."""
        return tuple(self._calls)

    async def complete(self, request: LlmRequest) -> LlmResponse:
        self._calls.append(request)
        text = self._responses.get(request.task)
        if text is None:
            raise LlmRequestError(f"MockLlmClient has no response for task '{request.task}'")
        return LlmResponse(
            text=text,
            provider=self.provider,
            model=self.model,
            usage=LlmUsage(input_tokens=0, output_tokens=0),
            latency_ms=0.0,
            finish_reason="stop",
        )
