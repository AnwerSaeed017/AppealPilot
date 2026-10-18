from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends

from app.containers.container import Container
from app.interfaces.service.sample_service import ISampleService
from app.interfaces.utilities.response_builder import IResponseBuilder
from app.schemas.api_response import ApiResponse
from app.schemas.sample_case import SampleCase

router = APIRouter(prefix="/samples", tags=["samples"])


@router.get("")
@inject
async def list_samples(
    sample_service: ISampleService = Depends(Provide[Container.services.sample_service]),
    response_builder: IResponseBuilder = Depends(Provide[Container.utilities.response_builder]),
) -> ApiResponse[tuple[SampleCase, ...]]:
    """Synthetic cases ready to submit, dated so their deadlines hold today."""
    return response_builder.success(await sample_service.list())
