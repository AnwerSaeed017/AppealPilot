from app.agents.states.case_state import CaseState
from app.interfaces.repository.case_repository import ICaseRepository
from app.interfaces.service.case_projection_service import ICaseProjectionService
from app.interfaces.utilities.clock import IClock
from app.schemas.case_status import CaseStatus
from app.schemas.case_summary import CaseSnapshot


class CaseProjectionService(ICaseProjectionService):
    def __init__(self, case_repository: ICaseRepository, clock: IClock) -> None:
        self._case_repository = case_repository
        self._clock = clock

    async def record(self, state: CaseState) -> None:
        await self._case_repository.save(CaseSnapshot.of(state), state.audit, self._clock.now())

    async def mark(self, case_id: str, status: CaseStatus) -> bool:
        return await self._case_repository.set_status(case_id, status, self._clock.now())
