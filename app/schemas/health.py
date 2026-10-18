from datetime import datetime
from typing import Literal

from app.schemas.base_schema import BaseSchema


class LivenessStatus(BaseSchema):
    status: Literal["alive"] = "alive"


class LlmRoleStatus(BaseSchema):
    provider: str
    model: str


class ReadinessStatus(BaseSchema):
    status: Literal["ready"] = "ready"
    checked_at: datetime
    database: Literal["ok"] = "ok"
    agent_llm: LlmRoleStatus
    judge_llm: LlmRoleStatus
