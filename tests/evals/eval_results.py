"""The shape of an evaluation run's saved results."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.draft import Draft
from app.schemas.recommended_action import RecommendedAction


class System(StrEnum):
    GRAPH = "graph"  # the full workflow
    BASELINE = "baseline"  # one prompt, same model, same clauses


class SystemResult(BaseModel):
    """What one system did with one case."""

    model_config = ConfigDict(extra="forbid")

    # The input failed validation, so no model was called.
    rejected: bool = False
    # Set when the run stopped on an error; the case then has no action.
    error: str | None = None
    action: RecommendedAction | None = None
    reasons: tuple[str, ...] = ()
    # Whether every assertion of the final draft passed verification (graph only).
    verified: bool | None = None
    # Citations of the final draft checked by code, and how many failed. Recorded for
    # both systems, so their citation quality can be compared without a model.
    citations: int = 0
    citations_failed: int = 0
    drafts: int = 0
    model_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    seconds: float = Field(default=0.0, description="Wall-clock time, including waits")
    draft: Draft | None = None


class CaseResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    scenario: str
    tags: tuple[str, ...] = ()
    expected: RecommendedAction | None
    acceptable: tuple[RecommendedAction, ...] = ()
    results: dict[System, SystemResult] = Field(default_factory=dict)


class RunInfo(BaseModel):
    """Recorded with every run, so a result can be traced to what produced it."""

    model_config = ConfigDict(extra="forbid")

    run: str
    started_at: datetime
    split: str
    case_set: str  # a hash of the case files
    agent_model: str
    judge_model: str
    prompt_versions: dict[str, str]
    retrieval: dict[str, int | bool]
