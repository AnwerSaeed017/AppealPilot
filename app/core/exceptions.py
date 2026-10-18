"""Domain errors. Services raise them; the exception handlers turn them into responses."""

from collections.abc import Sequence
from typing import ClassVar

from app.schemas.api_response import ErrorDetail


class DomainError(Exception):
    code: ClassVar[str] = "domain_error"

    def __init__(self, message: str, details: Sequence[ErrorDetail] = ()) -> None:
        super().__init__(message)
        self.message = message
        self.details = tuple(details)


class NotFoundError(DomainError):
    code = "not_found"


class ValidationFailedError(DomainError):
    code = "validation_failed"


class UnauthorizedError(DomainError):
    code = "unauthorized"


class ConflictError(DomainError):
    code = "conflict"


class ServiceUnavailableError(DomainError):
    code = "service_unavailable"


class AgentOutputError(DomainError):
    """A model did not return usable output within the allowed attempts."""

    code = "agent_output_invalid"


class ModelProviderError(DomainError):
    """The model provider could not be reached, refused the call, or returned nothing usable."""

    code = "model_provider_error"
