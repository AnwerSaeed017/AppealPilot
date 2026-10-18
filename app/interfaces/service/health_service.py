from abc import ABC, abstractmethod

from app.schemas.health import LivenessStatus, ReadinessStatus


class IHealthService(ABC):
    @abstractmethod
    def liveness(self) -> LivenessStatus:
        """The process is running. Checks no dependency."""

    @abstractmethod
    async def readiness(self) -> ReadinessStatus:
        """The service can take traffic. Raises ServiceUnavailableError when it cannot."""
