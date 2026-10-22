from app.core.exceptions import NotFoundError
from app.interfaces.repository.evaluation_repository import IEvaluationRepository
from app.interfaces.service.evaluation_service import IEvaluationService
from app.schemas.evaluation import EvaluationBenchmarks


class EvaluationService(IEvaluationService):
    def __init__(self, evaluation_repository: IEvaluationRepository) -> None:
        self._evaluation_repository = evaluation_repository

    async def get(self) -> EvaluationBenchmarks:
        benchmarks = await self._evaluation_repository.get()
        if benchmarks is None:
            raise NotFoundError("No evaluation results have been published.")
        return benchmarks
