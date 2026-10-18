from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.schemas.api_response import ApiResponse, ErrorDetail


class IResponseBuilder(ABC):
    """Builds the response envelope. Nothing else constructs an `ApiResponse`."""

    @abstractmethod
    def success[T](self, data: T) -> ApiResponse[T]:
        """Wrap a successful result."""

    @abstractmethod
    def failure(
        self, code: str, message: str, details: Sequence[ErrorDetail] = ()
    ) -> ApiResponse[None]:
        """Wrap an error."""
