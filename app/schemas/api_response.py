"""The one response envelope used by every endpoint, success or failure."""

from datetime import datetime

from app.schemas.base_schema import BaseSchema


class ErrorDetail(BaseSchema):
    field: str | None = None
    message: str


class ApiError(BaseSchema):
    code: str
    message: str
    details: tuple[ErrorDetail, ...] = ()


class ResponseMeta(BaseSchema):
    timestamp: datetime


class ApiResponse[T](BaseSchema):
    success: bool
    data: T | None = None
    error: ApiError | None = None
    meta: ResponseMeta
