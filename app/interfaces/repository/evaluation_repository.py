from abc import ABC, abstractmethod

from app.schemas.evaluation import EvaluationBenchmarks


class IEvaluationRepository(ABC):
    @abstractmethod
    async def get(self) -> EvaluationBenchmarks | None:
        """The published evaluation results, or None when none have been published."""
