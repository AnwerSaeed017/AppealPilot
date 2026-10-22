import logging
from collections.abc import Sequence

from app.clients.llm.errors import LlmAuthenticationError, LlmRateLimitError
from app.interfaces.clients.llm_client import ILlmClient
from app.schemas.llm import LlmRequest, LlmResponse

logger = logging.getLogger(__name__)


class RotatingLlmClient(ILlmClient):
    """One provider and model, reached through several API keys in turn.

    Calls go to the key that last worked. When it is rate-limited or its credentials are
    rejected, the next key is tried at once, so one exhausted or revoked key does not
    stop the service. Only when every key is rate-limited is the error passed on, with
    the shortest wait any key reported, for the retrying client around this one to
    honour. Keys are never logged; they are referred to by their position.

    Every client given must be for the same provider and model, so an answer does not
    depend on which key produced it, and cached answers stay valid across keys.
    """

    def __init__(self, clients: Sequence[ILlmClient]) -> None:
        if not clients:
            raise ValueError("RotatingLlmClient needs at least one client")
        identities = {(client.provider, client.model) for client in clients}
        if len(identities) > 1:
            raise ValueError("RotatingLlmClient needs clients for one provider and model")
        self._clients = tuple(clients)
        self._current = 0

    @property
    def provider(self) -> str:
        return self._clients[0].provider

    @property
    def model(self) -> str:
        return self._clients[0].model

    async def complete(self, request: LlmRequest) -> LlmResponse:
        limited: list[LlmRateLimitError] = []
        rejected: LlmAuthenticationError | None = None
        count = len(self._clients)
        for offset in range(count):
            index = (self._current + offset) % count
            try:
                response = await self._clients[index].complete(request)
            except LlmRateLimitError as error:
                limited.append(error)
                self._note_switch("rate-limited", index, count)
                continue
            except LlmAuthenticationError as error:
                rejected = error
                self._note_switch("rejected", index, count)
                continue
            self._current = index
            return response
        if limited:
            raise min(limited, key=_wait_or_unknown)
        assert rejected is not None
        raise rejected

    def _note_switch(self, reason: str, index: int, count: int) -> None:
        if count > 1:
            logger.warning(
                "%s key %d of %d was %s; trying the next key",
                self.provider,
                index + 1,
                count,
                reason,
            )


def _wait_or_unknown(error: LlmRateLimitError) -> float:
    """Order by the wait a provider asked for; an unknown wait goes last."""
    return error.retry_after_seconds if error.retry_after_seconds is not None else float("inf")
