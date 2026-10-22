from abc import ABC, abstractmethod

from app.schemas.evaluation import EvaluationBenchmarks


class IEvaluationService(ABC):
    @abstractmethod
    async def get(self) -> EvaluationBenchmarks:
        """The published evaluation results. Raises NotFoundError when there are none."""
