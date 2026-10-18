from pathlib import Path

from dependency_injector import providers

from app.clients.llm.caching_llm_client import CachingLlmClient
from app.clients.llm.mock_llm_client import MockLlmClient
from app.containers.container import Container
from app.core.settings import Settings
from app.services.health_service import HealthService


def container_with(settings: Settings) -> Container:
    container = Container()
    container.settings.override(providers.Object(settings))
    return container


def test_mock_roles_share_one_uncached_client() -> None:
    container = container_with(
        Settings(_env_file=None, agent_llm_provider="mock", judge_llm_provider="mock")
    )

    agent_llm = container.clients.agent_llm()

    assert isinstance(agent_llm, MockLlmClient)
    assert container.clients.judge_llm() is agent_llm


def test_real_providers_are_selected_per_role_and_cached(tmp_path: Path) -> None:
    container = container_with(
        Settings(
            _env_file=None,
            agent_llm_provider="groq",
            agent_llm_model="agent-model",
            groq_api_key="test-key",
            judge_llm_provider="gemini",
            judge_llm_model="judge-model",
            gemini_api_key="test-key",
            llm_cache_dir=tmp_path,
        )
    )

    agent_llm = container.clients.agent_llm()
    judge_llm = container.clients.judge_llm()

    assert isinstance(agent_llm, CachingLlmClient)
    assert (agent_llm.provider, agent_llm.model) == ("groq", "agent-model")
    assert isinstance(judge_llm, CachingLlmClient)
    assert (judge_llm.provider, judge_llm.model) == ("gemini", "judge-model")
    assert container.clients.agent_llm() is agent_llm


def test_services_are_built_from_the_layer_containers() -> None:
    container = container_with(
        Settings(
            _env_file=None,
            database_url="sqlite+aiosqlite:///:memory:",
            agent_llm_provider="mock",
            judge_llm_provider="mock",
        )
    )

    assert isinstance(container.services.health_service(), HealthService)
