from enum import StrEnum
from typing import Self

from pydantic import Field, model_validator

from app.schemas.base_schema import BaseSchema


class HumanDecisionKind(StrEnum):
    APPROVE = "APPROVE"
    EDIT_AND_APPROVE = "EDIT_AND_APPROVE"
    REJECT = "REJECT"


class HumanDecision(BaseSchema):
    """What the reviewer decided at the approval gate."""

    kind: HumanDecisionKind
    # Required when rejecting.
    reason: str | None = Field(default=None, min_length=1, max_length=2000)
    # Required when editing: the reviewer's own wording of the summary.
    edited_summary: str | None = Field(default=None, min_length=1, max_length=20000)

    @model_validator(mode="after")
    def _check_required_parts(self) -> Self:
        if self.kind is HumanDecisionKind.REJECT and self.reason is None:
            raise ValueError("a reason is required when rejecting")
        if (self.kind is HumanDecisionKind.EDIT_AND_APPROVE) != (self.edited_summary is not None):
            raise ValueError("edited_summary is set exactly when the decision is an edit")
        return self
