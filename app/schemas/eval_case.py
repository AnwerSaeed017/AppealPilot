from datetime import date
from enum import StrEnum
from typing import Any, Self

from pydantic import Field, ValidationError, model_validator

from app.schemas.base_schema import BaseSchema
from app.schemas.case_input import CaseInput
from app.schemas.code_types import ClauseId
from app.schemas.recommended_action import RecommendedAction


class EvalSplit(StrEnum):
    DEV = "dev"
    LOCKED = "locked"


class EvidenceRef(BaseSchema):
    """One line of a document: "NOTE" for the visit note, or a supporting document ID."""

    document_id: str
    line_number: int = Field(ge=1)


class ExpectedOutcome(BaseSchema):
    """The label for one case, written before any agent exists."""

    # None means the input is invalid and must be rejected before any model call.
    action: RecommendedAction | None
    # Other actions a reviewer would also accept. Anything else is wrong.
    acceptable_alternatives: tuple[RecommendedAction, ...] = ()
    relevant_clause_ids: tuple[ClauseId, ...] = ()
    supporting_evidence: tuple[EvidenceRef, ...] = ()
    missing_evidence: tuple[str, ...] = ()
    expected_correction: str | None = None
    rationale: str = Field(min_length=1)

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        if self.action in self.acceptable_alternatives:
            raise ValueError("an alternative must differ from the expected action")
        if self.action is None and (self.relevant_clause_ids or self.acceptable_alternatives):
            raise ValueError("an invalid-input case has no clauses and no alternatives")
        is_correction = self.action is RecommendedAction.CORRECT_AND_RESUBMIT
        if is_correction != (self.expected_correction is not None):
            raise ValueError("expected_correction is set exactly when the action is a correction")
        asks_for_documents = self.action is RecommendedAction.REQUEST_DOCUMENTATION
        if asks_for_documents != bool(self.missing_evidence):
            raise ValueError(
                "missing_evidence is set exactly when the action requests documentation"
            )
        return self


class EvalCase(BaseSchema):
    case_id: str = Field(pattern=r"^[A-Z]+-[0-9]{3}$")
    split: EvalSplit
    scenario: str = Field(min_length=1)
    tags: tuple[str, ...] = ()
    # The date the case is worked on. Deadlines are judged against it.
    as_of_date: date
    # Kept as raw JSON so that invalid-input cases can be represented.
    input: dict[str, Any]
    expected: ExpectedOutcome

    def case_input(self) -> CaseInput:
        return CaseInput.model_validate(self.input)

    @model_validator(mode="after")
    def _input_matches_label(self) -> Self:
        if self.expected.action is None:
            try:
                self.case_input()
            except ValidationError:
                return self
            raise ValueError("an invalid-input case must fail input validation")

        case_input = self.case_input()
        for reference in self.expected.supporting_evidence:
            text = case_input.document_text(reference.document_id)
            if text is None:
                raise ValueError(f"evidence refers to unknown document {reference.document_id}")
            if reference.line_number > len(text.splitlines()):
                raise ValueError(
                    f"evidence refers to line {reference.line_number} of "
                    f"{reference.document_id}, which has fewer lines"
                )
        if case_input.denial.denial_date > self.as_of_date:
            raise ValueError("as_of_date must not be before the denial date")
        return self
