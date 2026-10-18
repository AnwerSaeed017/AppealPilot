from enum import StrEnum
from typing import Self

from pydantic import Field, model_validator

from app.schemas.base_schema import BaseSchema
from app.schemas.code_types import ClauseId
from app.schemas.draft import Draft


class PlantedError(StrEnum):
    """The kinds of unsupported assertion planted in a draft."""

    # Caught by the code check: the citation itself is wrong.
    INVENTED_CLAUSE = "INVENTED_CLAUSE"
    CLAUSE_NOT_SELECTED = "CLAUSE_NOT_SELECTED"
    FABRICATED_QUOTE = "FABRICATED_QUOTE"
    NUMBER_CHANGED_IN_QUOTE = "NUMBER_CHANGED_IN_QUOTE"
    # Only a judge can catch these: the quote is real, the assertion goes beyond it.
    NUMBER_CHANGED_IN_ASSERTION = "NUMBER_CHANGED_IN_ASSERTION"
    HEDGE_REMOVED = "HEDGE_REMOVED"
    CONCLUSION_ADDED = "CONCLUSION_ADDED"


CODE_CATCHABLE = frozenset(
    {
        PlantedError.INVENTED_CLAUSE,
        PlantedError.CLAUSE_NOT_SELECTED,
        PlantedError.FABRICATED_QUOTE,
        PlantedError.NUMBER_CHANGED_IN_QUOTE,
    }
)


class PlantedDraft(BaseSchema):
    """A draft for one evaluation case, with at most one planted error.

    A draft with no planted error is a clean control: a verifier that flags it has
    raised a false alarm.
    """

    planted_id: str = Field(pattern=r"^PLANT-[0-9]{3}$")
    case_id: str
    # The clauses the verifier is told were selected for the case.
    selected_clause_ids: tuple[ClauseId, ...]
    draft: Draft
    error: PlantedError | None = None
    # Which assertion carries the error. None exactly when the draft is a clean control.
    planted_assertion_index: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _error_and_index_go_together(self) -> Self:
        if (self.error is None) != (self.planted_assertion_index is None):
            raise ValueError("error and planted_assertion_index are set together or not at all")
        if self.planted_assertion_index is not None and self.planted_assertion_index >= len(
            self.draft.assertions
        ):
            raise ValueError("planted_assertion_index is outside the draft's assertions")
        return self

    @property
    def catchable_by_code(self) -> bool:
        return self.error in CODE_CATCHABLE
