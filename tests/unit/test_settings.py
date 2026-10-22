from typing import Any

import pytest
from pydantic import ValidationError

from app.core.settings import Settings


def build(**values: Any) -> Settings:
    """Settings from explicit values only, ignoring env/.env."""
    return Settings(_env_file=None, **values)


def test_defaults_boot_without_any_credentials() -> None:
    settings = build(agent_llm_provider="mock", judge_llm_provider="mock")

    assert settings.agent_llm_model is None
    assert settings.llm_cache_enabled is True


def test_blank_values_from_an_env_file_count_as_unset() -> None:
    settings = build(
        agent_llm_provider="mock",
        judge_llm_provider="mock",
        agent_llm_model="  ",
        groq_api_key="",
    )

    assert settings.agent_llm_model is None
    assert settings.groq_api_key is None


def test_real_provider_requires_a_model() -> None:
    with pytest.raises(ValidationError, match="AGENT_LLM_MODEL is required"):
        build(agent_llm_provider="ollama", judge_llm_provider="mock")


def test_hosted_provider_requires_its_api_key() -> None:
    with pytest.raises(ValidationError, match="GROQ_API_KEY or GROQ_API_KEYS is required"):
        build(agent_llm_provider="groq", agent_llm_model="some-model", judge_llm_provider="mock")


def test_judge_must_use_a_different_provider_from_the_agents() -> None:
    with pytest.raises(ValidationError, match="JUDGE_LLM_PROVIDER must differ"):
        build(
            agent_llm_provider="ollama",
            agent_llm_model="model-a",
            judge_llm_provider="ollama",
            judge_llm_model="model-b",
        )


def test_shared_provider_is_allowed_when_asked_for() -> None:
    settings = build(
        agent_llm_provider="ollama",
        agent_llm_model="model-a",
        judge_llm_provider="ollama",
        judge_llm_model="model-b",
        allow_shared_llm_provider=True,
    )

    assert settings.judge_llm_model == "model-b"


def test_api_keys_are_not_exposed_by_repr() -> None:
    settings = build(
        agent_llm_provider="groq",
        agent_llm_model="some-model",
        judge_llm_provider="mock",
        groq_api_key="super-secret-value",
    )

    assert "super-secret-value" not in repr(settings)


def test_several_keys_are_read_from_one_comma_separated_setting() -> None:
    settings = build(
        agent_llm_provider="groq",
        agent_llm_model="some-model",
        judge_llm_provider="mock",
        groq_api_keys=" key-1, key-2 ,,key-1, key-3 ",
    )

    assert settings.provider_keys("groq") == ("key-1", "key-2", "key-3")


def test_the_single_key_joins_the_list_after_it_without_repeats() -> None:
    settings = build(
        agent_llm_provider="groq",
        agent_llm_model="some-model",
        judge_llm_provider="mock",
        groq_api_keys="key-1,key-2",
        groq_api_key="key-2",
    )

    assert settings.provider_keys("groq") == ("key-1", "key-2")


def test_a_list_of_keys_alone_is_enough() -> None:
    settings = build(
        agent_llm_provider="mock",
        judge_llm_provider="gemini",
        judge_llm_model="judge",
        gemini_api_keys="g-1,g-2",
    )

    assert settings.provider_keys("gemini") == ("g-1", "g-2")
