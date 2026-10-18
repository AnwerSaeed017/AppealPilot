from pydantic import Field

from app.schemas.base_schema import BaseSchema
from app.schemas.recommended_action import RecommendedAction


class TriageDecision(BaseSchema):
    """Which of the five actions the case calls for, and why."""

    action: RecommendedAction
    confidence: float = Field(ge=0.0, le=1.0)
    reasons: tuple[str, ...] = Field(min_length=1)
