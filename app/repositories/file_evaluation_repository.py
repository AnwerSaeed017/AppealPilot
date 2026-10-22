import asyncio
from pathlib import Path

from app.constants.policy_files import FILE_ENCODING
from app.interfaces.repository.evaluation_repository import IEvaluationRepository
from app.schemas.evaluation import EvaluationBenchmarks


class FileEvaluationRepository(IEvaluationRepository):
    """Published evaluation results from a versioned file, read once per process.

    The file is written by `scripts/publish_evaluation.py` and changes only with a
    deployment, so every process holds the same copy.
    """

    def __init__(self, evaluations_file: Path) -> None:
        self._evaluations_file = evaluations_file
        self._loaded = False
        self._benchmarks: EvaluationBenchmarks | None = None

    async def get(self) -> EvaluationBenchmarks | None:
        if not self._loaded:
            self._benchmarks = await asyncio.to_thread(self._read)
            self._loaded = True
        return self._benchmarks

    def _read(self) -> EvaluationBenchmarks | None:
        if not self._evaluations_file.is_file():
            return None
        return EvaluationBenchmarks.model_validate_json(
            self._evaluations_file.read_text(encoding=FILE_ENCODING)
        )
