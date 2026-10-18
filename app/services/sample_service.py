from datetime import date

from app.interfaces.repository.sample_repository import ISampleRepository
from app.interfaces.service.sample_service import ISampleService
from app.interfaces.utilities.clock import IClock
from app.interfaces.utilities.date_shifter import IDateShifter
from app.schemas.case_input import CaseInput
from app.schemas.sample_case import SampleCase


class SampleService(ISampleService):
    def __init__(
        self, sample_repository: ISampleRepository, date_shifter: IDateShifter, clock: IClock
    ) -> None:
        self._sample_repository = sample_repository
        self._date_shifter = date_shifter
        self._clock = clock

    async def list(self) -> tuple[SampleCase, ...]:
        today = self._clock.now().date()
        return tuple(self._as_of(sample, today) for sample in await self._sample_repository.list())

    def _as_of(self, sample: SampleCase, today: date) -> SampleCase:
        days = (today - sample.as_of_date).days
        moved = self._date_shifter.shift(sample.input.model_dump(mode="json"), days)
        # Validated again: the moved case must still be a valid submission.
        return sample.model_copy(
            update={"as_of_date": today, "input": CaseInput.model_validate(moved)}
        )
