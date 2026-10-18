from collections.abc import AsyncIterator
from http import HTTPStatus

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.constants.cases import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    STREAM_EVENT_STATUS,
    STREAM_EVENT_STEP,
)
from app.containers.container import Container
from app.interfaces.service.case_service import ICaseService
from app.interfaces.utilities.response_builder import IResponseBuilder
from app.schemas.api_response import ApiResponse
from app.schemas.case_input import CaseInput
from app.schemas.case_status import CaseStatus
from app.schemas.case_summary import CaseEvent, CasePage, CaseView
from app.schemas.human_decision import HumanDecision

router = APIRouter(prefix="/cases", tags=["cases"])


@router.post("", status_code=HTTPStatus.ACCEPTED)
@inject
async def submit_case(
    case_input: CaseInput,
    case_service: ICaseService = Depends(Provide[Container.case_service]),
    response_builder: IResponseBuilder = Depends(Provide[Container.utilities.response_builder]),
) -> ApiResponse[CaseView]:
    """Submit a denied claim. The case starts running and this returns at once."""
    return response_builder.success(await case_service.submit(case_input))


@router.get("")
@inject
async def list_cases(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    status: CaseStatus | None = None,
    case_service: ICaseService = Depends(Provide[Container.case_service]),
    response_builder: IResponseBuilder = Depends(Provide[Container.utilities.response_builder]),
) -> ApiResponse[CasePage]:
    return response_builder.success(await case_service.list(page, page_size, status))


@router.get("/{case_id}")
@inject
async def get_case(
    case_id: str,
    case_service: ICaseService = Depends(Provide[Container.case_service]),
    response_builder: IResponseBuilder = Depends(Provide[Container.utilities.response_builder]),
) -> ApiResponse[CaseView]:
    return response_builder.success(await case_service.get(case_id))


@router.get("/{case_id}/events")
@inject
async def follow_case(
    case_id: str,
    case_service: ICaseService = Depends(Provide[Container.case_service]),
) -> StreamingResponse:
    """Server-sent events: one `step` event per recorded step, then one `status` event
    when the case stops running."""
    # Look the case up before the stream starts, so an unknown case is a normal 404.
    await case_service.get(case_id)

    async def stream() -> AsyncIterator[str]:
        async for item in case_service.follow(case_id):
            name = STREAM_EVENT_STEP if isinstance(item, CaseEvent) else STREAM_EVENT_STATUS
            yield f"event: {name}\ndata: {item.model_dump_json()}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.post("/{case_id}/decision")
@inject
async def decide_case(
    case_id: str,
    decision: HumanDecision,
    case_service: ICaseService = Depends(Provide[Container.case_service]),
    response_builder: IResponseBuilder = Depends(Provide[Container.utilities.response_builder]),
) -> ApiResponse[CaseView]:
    """Approve, edit and approve, or reject a case that is waiting for a decision."""
    return response_builder.success(await case_service.decide(case_id, decision))


@router.post("/{case_id}/retry", status_code=HTTPStatus.ACCEPTED)
@inject
async def retry_case(
    case_id: str,
    case_service: ICaseService = Depends(Provide[Container.case_service]),
    response_builder: IResponseBuilder = Depends(Provide[Container.utilities.response_builder]),
) -> ApiResponse[CaseView]:
    """Continue a failed case from its last completed step."""
    return response_builder.success(await case_service.retry(case_id))
