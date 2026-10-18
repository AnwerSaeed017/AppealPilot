from abc import ABC, abstractmethod

from app.schemas.sample_case import SampleCase


class ISampleRepository(ABC):
    @abstractmethod
    async def list(self) -> tuple[SampleCase, ...]:
        """Every sample case, as written, in a stable order."""
