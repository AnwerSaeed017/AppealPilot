import asyncio
import os
import uuid
from pathlib import Path

from pydantic import ValidationError

from app.constants.llm import CACHE_KEY_PATTERN
from app.interfaces.clients.llm_cache import ILlmCache
from app.schemas.llm import LlmResponse


class DiskLlmCache(ILlmCache):
    """One JSON file per completion, safe for several processes sharing a directory."""

    def __init__(self, directory: Path) -> None:
        self._directory = directory

    async def get(self, key: str) -> LlmResponse | None:
        return await asyncio.to_thread(self._read, self._path(key))

    async def set(self, key: str, response: LlmResponse) -> None:
        await asyncio.to_thread(self._write, self._path(key), response)

    def _path(self, key: str) -> Path:
        if not CACHE_KEY_PATTERN.fullmatch(key):
            raise ValueError("cache key must be a SHA-256 hex digest")
        return self._directory / key[:2] / f"{key}.json"

    @staticmethod
    def _read(path: Path) -> LlmResponse | None:
        try:
            raw = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        try:
            return LlmResponse.model_validate_json(raw)
        except ValidationError:
            # A corrupt or outdated entry is a miss; the next write replaces it.
            return None

    @staticmethod
    def _write(path: Path, response: LlmResponse) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        # Write beside the target, then rename, so a reader never sees a partial file.
        temporary = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
        temporary.write_text(response.model_dump_json(), encoding="utf-8")
        os.replace(temporary, path)
