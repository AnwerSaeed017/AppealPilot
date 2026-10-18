import asyncio
from pathlib import Path

from app.constants.policy_files import FILE_ENCODING
from app.constants.samples import SAMPLE_FILE_GLOB
from app.interfaces.repository.sample_repository import ISampleRepository
from app.schemas.sample_case import SampleCase


class FileSampleRepository(ISampleRepository):
    """Sample cases from versioned files, read once and kept for the life of the process."""

    def __init__(self, samples_dir: Path) -> None:
        self._samples_dir = samples_dir
        self._samples: tuple[SampleCase, ...] | None = None

    async def list(self) -> tuple[SampleCase, ...]:
        if self._samples is None:
            self._samples = await asyncio.to_thread(self._read)
        return self._samples

    def _read(self) -> tuple[SampleCase, ...]:
        return tuple(
            SampleCase.model_validate_json(path.read_text(encoding=FILE_ENCODING))
            for path in sorted(self._samples_dir.glob(SAMPLE_FILE_GLOB))
        )
