from typing import Any

import httpx
from dependency_injector import containers, providers

from app.clients.llm.caching_llm_client import CachingLlmClient
from app.clients.llm.disk_llm_cache import DiskLlmCache
from app.clients.llm.gemini_llm_client import GeminiLlmClient
from app.clients.llm.groq_llm_client import GroqLlmClient
from app.clients.llm.mock_llm_client import MockLlmClient
from app.clients.llm.ollama_llm_client import OllamaLlmClient
from app.clients.llm.retrying_llm_client import RetryingLlmClient
from app.core.settings import Settings
from app.interfaces.clients.llm_client import ILlmClient


def _llm_for_role(
    settings: providers.Dependency[Settings],
    http_client: providers.Provider[httpx.AsyncClient],
    llm_cache: providers.Provider[DiskLlmCache],
    mock_llm: providers.Provider[MockLlmClient],
    provider_name: providers.Provider[Any],
    model: providers.Provider[Any],
) -> providers.Selector[ILlmClient]:
    """The client for one role, chosen by the provider named in settings.

    Real providers are wrapped twice: retries on the inside, the disk cache on the
    outside, so a cached answer never waits and a retried call is cached once it
    succeeds. The mock is wrapped in neither: its answers are scripted and instant.
    """

    def cached(inner: providers.Provider[ILlmClient]) -> providers.Singleton[CachingLlmClient]:
        return providers.Singleton(
            CachingLlmClient,
            inner=providers.Singleton(
                RetryingLlmClient,
                inner=inner,
                max_retries=settings.provided.llm_max_retries,
                base_delay_seconds=settings.provided.llm_retry_base_seconds,
                max_delay_seconds=settings.provided.llm_retry_max_seconds,
            ),
            cache=llm_cache,
            enabled=settings.provided.llm_cache_enabled,
        )

    timeout_seconds = settings.provided.llm_timeout_seconds
    return providers.Selector(
        provider_name,
        mock=mock_llm,
        groq=cached(
            providers.Singleton(
                GroqLlmClient,
                http_client=http_client,
                api_key=settings.provided.groq_api_key.get_secret_value.call(),
                base_url=settings.provided.groq_base_url,
                model=model,
                timeout_seconds=timeout_seconds,
                request_token_limit=settings.provided.groq_request_token_limit,
            )
        ),
        gemini=cached(
            providers.Singleton(
                GeminiLlmClient,
                http_client=http_client,
                api_key=settings.provided.gemini_api_key.get_secret_value.call(),
                base_url=settings.provided.gemini_base_url,
                model=model,
                timeout_seconds=timeout_seconds,
            )
        ),
        ollama=cached(
            providers.Singleton(
                OllamaLlmClient,
                http_client=http_client,
                base_url=settings.provided.ollama_base_url,
                model=model,
                timeout_seconds=timeout_seconds,
            )
        ),
    )


class ClientContainer(containers.DeclarativeContainer):
    """External services, each behind an interface."""

    settings = providers.Dependency(instance_of=Settings)

    http_client = providers.Singleton(httpx.AsyncClient)
    llm_cache = providers.Singleton(DiskLlmCache, directory=settings.provided.llm_cache_dir)
    mock_llm = providers.Singleton(MockLlmClient)

    agent_llm = _llm_for_role(
        settings,
        http_client,
        llm_cache,
        mock_llm,
        provider_name=settings.provided.agent_llm_provider,
        model=settings.provided.agent_llm_model,
    )
    judge_llm = _llm_for_role(
        settings,
        http_client,
        llm_cache,
        mock_llm,
        provider_name=settings.provided.judge_llm_provider,
        model=settings.provided.judge_llm_model,
    )
