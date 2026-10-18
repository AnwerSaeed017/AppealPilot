from datetime import datetime

from pydantic import Field

from app.schemas.base_schema import BaseSchema


class LlmCallRecord(BaseSchema):
    """What one model-backed step cost."""

    provider: str
    model: str
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    latency_ms: float = Field(ge=0)
    cached: bool
    # How many times the model was asked before its output was usable.
    attempts: int = Field(ge=1)


class AuditEvent(BaseSchema):
    """One step of a case's run. Steps that use no model have no `llm_call`."""

    step: str = Field(min_length=1)
    at: datetime
    summary: str = Field(min_length=1)
    llm_call: LlmCallRecord | None = None


class AgentResult[T](BaseSchema):
    """An agent's output together with what producing it cost."""

    output: T
    llm_call: LlmCallRecord
