from pathlib import Path

import pytest

from app.clients.llm.caching_llm_client import CachingLlmClient
from app.clients.llm.disk_llm_cache import DiskLlmCache
from app.interfaces.clients.llm_client import ILlmClient
from app.schemas.llm import LlmMessage, LlmRequest, LlmResponse, LlmUsage


class CountingLlmClient(ILlmClient):
    """Answers with a running call number, so a replay is distinguishable from a call."""

    def __init__(self, model: str = "model-a") -> None:
        self._model = model
        self.call_count = 0

    @property
    def provider(self) -> str:
        return "counting"

    @property
    def model(self) -> str:
        return self._model

    async def complete(self, request: LlmRequest) -> LlmResponse:
        self.call_count += 1
        return LlmResponse(
            text=f"answer {self.call_count}",
            provider=self.provider,
            model=self.model,
            usage=LlmUsage(input_tokens=10, output_tokens=5),
            latency_ms=120.0,
        )


def make_request(prompt_version: str = "1", content: str = "hello") -> LlmRequest:
    return LlmRequest(
        task="triage",
        prompt_version=prompt_version,
        messages=(LlmMessage(role="user", content=content),),
    )


async def test_identical_request_is_replayed_and_marked_cached(tmp_path: Path) -> None:
    inner = CountingLlmClient()
    client = CachingLlmClient(inner, DiskLlmCache(tmp_path))

    first = await client.complete(make_request())
    second = await client.complete(make_request())

    assert inner.call_count == 1
    assert first.cached is False
    assert second.cached is True
    assert second.text == "answer 1"
    assert second.usage == first.usage


async def test_cache_survives_a_new_client_instance(tmp_path: Path) -> None:
    await CachingLlmClient(CountingLlmClient(), DiskLlmCache(tmp_path)).complete(make_request())

    inner = CountingLlmClient()
    response = await CachingLlmClient(inner, DiskLlmCache(tmp_path)).complete(make_request())

    assert inner.call_count == 0
    assert response.cached is True


@pytest.mark.parametrize(
    "changed",
    [
        make_request(prompt_version="2"),
        make_request(content="different input"),
        make_request().model_copy(update={"temperature": 0.7}),
        make_request().model_copy(update={"json_output": True}),
    ],
)
async def test_any_change_to_the_request_is_a_fresh_call(
    tmp_path: Path, changed: LlmRequest
) -> None:
    inner = CountingLlmClient()
    client = CachingLlmClient(inner, DiskLlmCache(tmp_path))

    await client.complete(make_request())
    response = await client.complete(changed)

    assert inner.call_count == 2
    assert response.cached is False


async def test_a_different_model_does_not_share_entries(tmp_path: Path) -> None:
    cache = DiskLlmCache(tmp_path)
    await CachingLlmClient(CountingLlmClient("model-a"), cache).complete(make_request())

    other = CountingLlmClient("model-b")
    response = await CachingLlmClient(other, cache).complete(make_request())

    assert other.call_count == 1
    assert response.cached is False


async def test_disabled_cache_is_neither_read_nor_written(tmp_path: Path) -> None:
    inner = CountingLlmClient()
    client = CachingLlmClient(inner, DiskLlmCache(tmp_path), enabled=False)

    await client.complete(make_request())
    await client.complete(make_request())

    assert inner.call_count == 2
    assert list(tmp_path.iterdir()) == []


async def test_corrupt_entry_is_a_miss_and_gets_replaced(tmp_path: Path) -> None:
    inner = CountingLlmClient()
    client = CachingLlmClient(inner, DiskLlmCache(tmp_path))
    await client.complete(make_request())
    (entry,) = tmp_path.rglob("*.json")
    entry.write_text("{ not json", encoding="utf-8")

    refreshed = await client.complete(make_request())
    replayed = await client.complete(make_request())

    assert refreshed.cached is False
    assert replayed.cached is True
    assert inner.call_count == 2


async def test_failed_call_is_not_cached(tmp_path: Path) -> None:
    class FailingLlmClient(CountingLlmClient):
        async def complete(self, request: LlmRequest) -> LlmResponse:
            self.call_count += 1
            raise RuntimeError("provider down")

    inner = FailingLlmClient()
    client = CachingLlmClient(inner, DiskLlmCache(tmp_path))

    for _ in range(2):
        with pytest.raises(RuntimeError):
            await client.complete(make_request())

    assert inner.call_count == 2


async def test_cache_rejects_keys_that_are_not_digests(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="SHA-256"):
        await DiskLlmCache(tmp_path).get("../outside")
