import pytest

from app.clients.llm.mock_llm_client import MockLlmClient
from app.core.exceptions import ServiceUnavailableError
from app.services.health_service import HealthService
from tests.fakes import FIXED_NOW, FakeHealthRepository, FixedClock


def build_service(reachable: bool) -> HealthService:
    return HealthService(
        health_repository=FakeHealthRepository(reachable),
        clock=FixedClock(),
        agent_llm=MockLlmClient(),
        judge_llm=MockLlmClient(),
    )


def test_liveness_checks_nothing() -> None:
    assert build_service(reachable=False).liveness().status == "alive"


async def test_readiness_reports_the_configured_llm_roles() -> None:
    status = await build_service(reachable=True).readiness()

    assert status.checked_at == FIXED_NOW
    assert status.agent_llm.provider == "mock"
    assert status.judge_llm.model == "mock"


async def test_readiness_fails_when_the_database_is_down() -> None:
    with pytest.raises(ServiceUnavailableError):
        await build_service(reachable=False).readiness()
