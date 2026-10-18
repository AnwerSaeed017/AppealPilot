from abc import ABC, abstractmethod

from app.schemas.sample_case import SampleCase


class ISampleService(ABC):
    @abstractmethod
    async def list(self) -> tuple[SampleCase, ...]:
        """The sample cases, moved in time so that each behaves today as it was written to.

        Every date in a sample moves by the same number of days, so its deadlines are
        exactly as near or as far as they were on the day it was written for.
        """
