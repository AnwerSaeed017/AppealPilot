from pathlib import Path
from typing import Literal, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

from app.constants.database import POSTGRES_SCHEME, POSTGRES_SQLALCHEMY_DRIVER

LlmProvider = Literal["mock", "groq", "gemini", "ollama"]


class Settings(BaseSettings):
    """Every configurable value, read from the environment with env/.env as fallback."""

    model_config = SettingsConfigDict(
        env_file="env/.env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    app_name: str = "AppealPilot"
    environment: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    cors_allowed_origins: tuple[str, ...] = ()

    database_url: str = "sqlite+aiosqlite:///./appealpilot.db"
    database_echo: bool = False
    # Connections kept for saving workflow state. Small, to suit a free database tier.
    checkpoint_pool_max_size: int = Field(default=5, ge=1, le=50)

    # How often a live-progress stream looks for newly recorded steps.
    case_events_poll_seconds: float = Field(default=0.5, gt=0, le=10)

    policies_dir: Path = Path("seeders/policies")
    samples_dir: Path = Path("seeders/samples")
    evaluations_file: Path = Path("seeders/evaluations/benchmarks.json")
    retrieval_limit: int = Field(default=5, ge=1, le=20)
    retrieval_include_visit_note: bool = False
    # How many of the top clauses bring the next clause of their section with them.
    retrieval_neighbour_sources: int = Field(default=1, ge=0, le=5)
    # How many clauses the second search, on facts from supporting documents, may add.
    retrieval_document_additions: int = Field(default=2, ge=0, le=5)

    agent_llm_provider: LlmProvider = "mock"
    agent_llm_model: str | None = None
    judge_llm_provider: LlmProvider = "mock"
    judge_llm_model: str | None = None
    allow_shared_llm_provider: bool = False

    groq_api_key: SecretStr | None = None
    groq_base_url: str = "https://api.groq.com/openai/v1"
    # The most tokens one Groq request may count against the account's per-minute limit:
    # the prompt plus the reply allowance. Set it to the plan's tokens-per-minute limit
    # (8000 on the free tier) so each reply allowance is sized to fit; unset, requests
    # keep the allowance each step asks for.
    groq_request_token_limit: int | None = Field(default=None, gt=0)
    gemini_api_key: SecretStr | None = None
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    ollama_base_url: str = "http://localhost:11434"

    llm_timeout_seconds: float = Field(default=60.0, gt=0)
    # Retries of a model call after a rate limit, timeout or provider-side error.
    llm_max_retries: int = Field(default=6, ge=0, le=10)
    llm_retry_base_seconds: float = Field(default=2.0, gt=0)
    llm_retry_max_seconds: float = Field(default=60.0, gt=0)
    llm_cache_enabled: bool = True
    llm_cache_dir: Path = Path(".cache/llm")

    @property
    def sqlalchemy_database_url(self) -> str:
        """The database address with the driver SQLAlchemy should use."""
        url = make_url(self.database_url)
        if url.drivername == POSTGRES_SCHEME:
            url = url.set(drivername=POSTGRES_SQLALCHEMY_DRIVER)
        return url.render_as_string(hide_password=False)

    @property
    def postgres_dsn(self) -> str:
        """The plain PostgreSQL address, as the workflow's checkpoint store needs it."""
        url = make_url(self.database_url)
        if not url.drivername.startswith(POSTGRES_SCHEME):
            raise ValueError(
                "Workflow state is kept in PostgreSQL. Set DATABASE_URL to a postgresql:// address."
            )
        return url.set(drivername=POSTGRES_SCHEME).render_as_string(hide_password=False)

    @field_validator(
        "agent_llm_model", "judge_llm_model", "groq_api_key", "gemini_api_key", mode="before"
    )
    @classmethod
    def _blank_is_unset(cls, value: object) -> object:
        """An empty line in an env file (`GROQ_API_KEY=`) means "not set"."""
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @model_validator(mode="after")
    def _check_llm_roles(self) -> Self:
        roles = (
            ("AGENT", self.agent_llm_provider, self.agent_llm_model),
            ("JUDGE", self.judge_llm_provider, self.judge_llm_model),
        )
        api_keys = {"groq": self.groq_api_key, "gemini": self.gemini_api_key}
        for role, provider, model in roles:
            if provider == "mock":
                continue
            if model is None:
                raise ValueError(f"{role}_LLM_MODEL is required when the provider is {provider}")
            if provider in api_keys and api_keys[provider] is None:
                raise ValueError(
                    f"{provider.upper()}_API_KEY is required when {role}_LLM_PROVIDER is {provider}"
                )

        # A judge on the same provider as the agents grades its own work and
        # shares one free quota, so it has to be asked for explicitly.
        if (
            self.agent_llm_provider == self.judge_llm_provider
            and self.agent_llm_provider != "mock"
            and not self.allow_shared_llm_provider
        ):
            raise ValueError(
                "JUDGE_LLM_PROVIDER must differ from AGENT_LLM_PROVIDER "
                "unless ALLOW_SHARED_LLM_PROVIDER is true"
            )
        return self
