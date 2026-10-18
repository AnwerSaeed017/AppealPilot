from collections.abc import Sequence

from app.interfaces.utilities.clock import IClock
from app.interfaces.utilities.response_builder import IResponseBuilder
from app.schemas.api_response import ApiError, ApiResponse, ErrorDetail, ResponseMeta


class ResponseBuilder(IResponseBuilder):
    def __init__(self, clock: IClock) -> None:
        self._clock = clock

    def success[T](self, data: T) -> ApiResponse[T]:
        return ApiResponse[T](success=True, data=data, meta=self._meta())

    def failure(
        self, code: str, message: str, details: Sequence[ErrorDetail] = ()
    ) -> ApiResponse[None]:
        return ApiResponse[None](
            success=False,
            error=ApiError(code=code, message=message, details=tuple(details)),
            meta=self._meta(),
        )

    def _meta(self) -> ResponseMeta:
        return ResponseMeta(timestamp=self._clock.now())
