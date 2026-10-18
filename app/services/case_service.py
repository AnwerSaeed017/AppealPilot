import asyncio
import logging
from collections.abc import AsyncIterator
from datetime import date

from app.agents.states.case_state import CaseState
from app.core.exceptions import ConflictError, NotFoundError
from app.interfaces.agents.case_workflow import ICaseWorkflow
from app.interfaces.repository.case_repository import ICaseRepository
from app.interfaces.service.case_projection_service import ICaseProjectionService
from app.interfaces.service.case_service import ICaseService
from app.interfaces.utilities.clock import IClock
from app.interfaces.utilities.id_generator import IIdGenerator
from app.interfaces.utilities.task_runner import ITaskRunner
from app.schemas.case_input import CaseInput
from app.schemas.case_status import CaseStatus
from app.schemas.case_summary import CaseEvent, CasePage, CaseSummary, CaseView
from app.schemas.human_decision import HumanDecision

logger = logging.getLogger(__name__)


class CaseService(ICaseService):
    """What the outside world can do with a case.

    The case ID and the working date are set here, by the server. A client never
    supplies either. A case runs in the background, because its model calls take longer
    than a request should wait; its progress is recorded step by step in the case
    tables, where the list, the live stream and a page refresh all read it.
    """

    def __init__(
        self,
        workflow: ICaseWorkflow,
        projection: ICaseProjectionService,
        case_repository: ICaseRepository,
        clock: IClock,
        id_generator: IIdGenerator,
        task_runner: ITaskRunner,
        poll_seconds: float,
    ) -> None:
        self._workflow = workflow
        self._projection = projection
        self._case_repository = case_repository
        self._clock = clock
        self._id_generator = id_generator
        self._task_runner = task_runner
        self._poll_seconds = poll_seconds

    async def submit(self, case_input: CaseInput) -> CaseView:
        case_id = self._id_generator.new_id()
        as_of = self._clock.now().date()
        # Record the case before answering, so it can be found from the first moment.
        await self._projection.record(
            CaseState(case_id=case_id, as_of=as_of, case_input=case_input)
        )
        self._task_runner.start(self._run(case_id, case_input, as_of))
        return await self.get(case_id)

    async def get(self, case_id: str) -> CaseView:
        summary = await self._summary(case_id)
        state = await self._workflow.get(case_id)
        if state is not None and state.status is not summary.status:
            # The working state does not know about a failure or a retry; the record does.
            state = state.model_copy(update={"status": summary.status})
        return CaseView(summary=summary, state=state)

    async def list(self, page: int, page_size: int, status: CaseStatus | None) -> CasePage:
        return await self._case_repository.list(page, page_size, status)

    async def decide(self, case_id: str, decision: HumanDecision) -> CaseView:
        await self._summary(case_id)
        await self._workflow.resume(case_id, decision)
        return await self.get(case_id)

    async def retry(self, case_id: str) -> CaseView:
        summary = await self._summary(case_id)
        if summary.status is not CaseStatus.FAILED:
            raise ConflictError(f"Case {case_id} has not failed, so there is nothing to retry.")
        await self._projection.mark(case_id, CaseStatus.RUNNING)
        self._task_runner.start(self._continue(case_id))
        return await self.get(case_id)

    async def follow(self, case_id: str) -> AsyncIterator[CaseEvent | CaseSummary]:
        await self._summary(case_id)
        last_sequence = 0
        while True:
            # Read the status first: steps recorded before it are then certain to be
            # picked up below, so none is missed when the run ends between the two reads.
            summary = await self._summary(case_id)
            for event in await self._case_repository.list_events(case_id, last_sequence):
                last_sequence = event.sequence
                yield event
            if summary.status is not CaseStatus.RUNNING:
                yield summary
                return
            await asyncio.sleep(self._poll_seconds)

    async def _summary(self, case_id: str) -> CaseSummary:
        summary = await self._case_repository.get(case_id)
        if summary is None:
            raise NotFoundError(f"Case {case_id} does not exist.")
        return summary

    async def _run(self, case_id: str, case_input: CaseInput, as_of: date) -> None:
        try:
            await self._workflow.start(case_id, case_input, as_of)
        except Exception:
            await self._failed(case_id)

    async def _continue(self, case_id: str) -> None:
        try:
            await self._workflow.continue_run(case_id)
        except Exception:
            await self._failed(case_id)

    async def _failed(self, case_id: str) -> None:
        # Nobody is waiting on a background run, so the error is logged here and the
        # case is marked, where the list and the stream will show it.
        logger.exception("Case %s stopped on an error", case_id)
        await self._projection.mark(case_id, CaseStatus.FAILED)
