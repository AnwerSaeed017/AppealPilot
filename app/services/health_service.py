from app.core.exceptions import ServiceUnavailableError
from app.interfaces.clients.llm_client import ILlmClient
from app.interfaces.repository.health_repository import IHealthRepository
from app.interfaces.service.health_service import IHealthService
from app.interfaces.utilities.clock import IClock
from app.schemas.health import LivenessStatus, LlmRoleStatus, ReadinessStatus


class HealthService(IHealthService):
    def __init__(
        self,
        health_repository: IHealthRepository,
        clock: IClock,
        agent_llm: ILlmClient,
        judge_llm: ILlmClient,
    ) -> None:
        self._health_repository = health_repository
        self._clock = clock
        self._agent_llm = agent_llm
        self._judge_llm = judge_llm

    def liveness(self) -> LivenessStatus:
        return LivenessStatus()

    async def readiness(self) -> ReadinessStatus:
        if not await self._health_repository.is_database_reachable():
            raise ServiceUnavailableError("The database is not reachable.")
        return ReadinessStatus(
            checked_at=self._clock.now(),
            agent_llm=self._describe(self._agent_llm),
            judge_llm=self._describe(self._judge_llm),
        )

    @staticmethod
    def _describe(client: ILlmClient) -> LlmRoleStatus:
        return LlmRoleStatus(provider=client.provider, model=client.model)
