import hashlib
import json
import time

from app.interfaces.clients.llm_cache import ILlmCache
from app.interfaces.clients.llm_client import ILlmClient
from app.schemas.llm import LlmRequest, LlmResponse


class CachingLlmClient(ILlmClient):
    """Wraps another client and replays stored completions for identical requests.

    The key covers the provider, the model and every request field, so changing the
    model, the prompt version or any input produces a fresh call. Replayed responses
    are marked `cached=True`. With `enabled=False` the cache is neither read nor
    written.
    """

    def __init__(self, inner: ILlmClient, cache: ILlmCache, enabled: bool = True) -> None:
        self._inner = inner
        self._cache = cache
        self._enabled = enabled

    @property
    def provider(self) -> str:
        return self._inner.provider

    @property
    def model(self) -> str:
        return self._inner.model

    async def complete(self, request: LlmRequest) -> LlmResponse:
        if not self._enabled:
            return await self._inner.complete(request)

        key = self._key(request)
        started = time.perf_counter()
        stored = await self._cache.get(key)
        if stored is not None:
            return stored.model_copy(
                update={"cached": True, "latency_ms": (time.perf_counter() - started) * 1000}
            )

        response = await self._inner.complete(request)
        await self._cache.set(key, response)
        return response

    def _key(self, request: LlmRequest) -> str:
        material = {
            "provider": self._inner.provider,
            "model": self._inner.model,
            "request": request.model_dump(mode="json"),
        }
        canonical = json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
