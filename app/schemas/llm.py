"""Value types exchanged with an LLM client."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

LlmRole = Literal["system", "user", "assistant"]

# How much a reasoning model may think before it answers. Providers that do not support
# it ignore it.
ReasoningEffort = Literal["low", "medium", "high"]


class LlmMessage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    role: LlmRole
    content: str = Field(min_length=1)


class LlmRequest(BaseModel):
    """One completion call.

    `task` names the call site (for example "triage") and `prompt_version` changes
    whenever the prompt text does. Both are part of the cache key and the audit trail.
    The model is not part of the request: each client is bound to one model.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    task: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    messages: tuple[LlmMessage, ...] = Field(min_length=1)
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_output_tokens: int = Field(default=1024, gt=0)
    json_output: bool = False
    # None leaves the provider's default.
    reasoning_effort: ReasoningEffort | None = None


class LlmUsage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)


class LlmResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str
    provider: str
    model: str
    usage: LlmUsage
    latency_ms: float = Field(ge=0)
    finish_reason: str | None = None
    cached: bool = False
