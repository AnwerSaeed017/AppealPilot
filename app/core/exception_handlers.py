import logging
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.core.exceptions import (
    AgentOutputError,
    ConflictError,
    DomainError,
    ModelProviderError,
    NotFoundError,
    ServiceUnavailableError,
    UnauthorizedError,
    ValidationFailedError,
)
from app.interfaces.utilities.response_builder import IResponseBuilder
from app.schemas.api_response import ApiResponse, ErrorDetail

logger = logging.getLogger(__name__)

_STATUS_BY_ERROR: dict[type[DomainError], int] = {
    NotFoundError: HTTPStatus.NOT_FOUND,
    ValidationFailedError: HTTPStatus.UNPROCESSABLE_ENTITY,
    UnauthorizedError: HTTPStatus.UNAUTHORIZED,
    ConflictError: HTTPStatus.CONFLICT,
    ServiceUnavailableError: HTTPStatus.SERVICE_UNAVAILABLE,
    AgentOutputError: HTTPStatus.BAD_GATEWAY,
    ModelProviderError: HTTPStatus.BAD_GATEWAY,
}


def register_exception_handlers(app: FastAPI, response_builder: IResponseBuilder) -> None:
    """Convert every error into the standard envelope, in this one place."""

    def respond(status: int, envelope: ApiResponse[None]) -> JSONResponse:
        return JSONResponse(status_code=status, content=envelope.model_dump(mode="json"))

    async def handle_domain_error(_: Request, error: Exception) -> JSONResponse:
        if not isinstance(error, DomainError):
            raise error
        status = next(
            (code for kind, code in _STATUS_BY_ERROR.items() if isinstance(error, kind)),
            HTTPStatus.BAD_REQUEST,
        )
        return respond(status, response_builder.failure(error.code, error.message, error.details))

    async def handle_request_validation(_: Request, error: Exception) -> JSONResponse:
        if not isinstance(error, RequestValidationError):
            raise error
        # Report where and why, but never echo the submitted value back.
        details = [
            ErrorDetail(
                field=".".join(str(part) for part in item["loc"]),
                message=str(item["msg"]),
            )
            for item in error.errors()
        ]
        return respond(
            HTTPStatus.UNPROCESSABLE_ENTITY,
            response_builder.failure(
                ValidationFailedError.code, "The request is not valid.", details
            ),
        )

    async def handle_http_exception(_: Request, error: Exception) -> JSONResponse:
        if not isinstance(error, HTTPException):
            raise error
        phrase = HTTPStatus(error.status_code).phrase
        return respond(
            error.status_code,
            response_builder.failure(phrase.lower().replace(" ", "_"), phrase),
        )

    async def handle_unexpected(_: Request, error: Exception) -> JSONResponse:
        logger.exception("Unhandled error", exc_info=error)
        return respond(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            response_builder.failure("internal_error", "An unexpected error occurred."),
        )

    app.add_exception_handler(DomainError, handle_domain_error)
    app.add_exception_handler(RequestValidationError, handle_request_validation)
    app.add_exception_handler(HTTPException, handle_http_exception)
    app.add_exception_handler(Exception, handle_unexpected)
