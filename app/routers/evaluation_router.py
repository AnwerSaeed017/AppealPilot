from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends

from app.containers.container import Container
from app.interfaces.service.evaluation_service import IEvaluationService
from app.interfaces.utilities.response_builder import IResponseBuilder
from app.schemas.api_response import ApiResponse
from app.schemas.evaluation import EvaluationBenchmarks

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


@router.get("")
@inject
async def get_evaluations(
    evaluation_service: IEvaluationService = Depends(
        Provide[Container.services.evaluation_service]
    ),
    response_builder: IResponseBuilder = Depends(Provide[Container.utilities.response_builder]),
) -> ApiResponse[EvaluationBenchmarks]:
    """The published comparison of the workflow with a single-prompt baseline."""
    return response_builder.success(await evaluation_service.get())
