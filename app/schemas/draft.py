from enum import StrEnum

from pydantic import Field

from app.schemas.base_schema import BaseSchema
from app.schemas.recommended_action import RecommendedAction


class CitationKind(StrEnum):
    CLAUSE = "CLAUSE"  # a policy clause, by clause ID
    DOCUMENT = "DOCUMENT"  # the visit note ("NOTE") or a supporting document, by ID


class Citation(BaseSchema):
    """Where an assertion comes from: a source and the exact words relied on."""

    kind: CitationKind
    source_id: str = Field(min_length=1)
    quote: str = Field(min_length=1)


class Assertion(BaseSchema):
    """One factual statement in a draft. It must carry at least one citation."""

    text: str = Field(min_length=1)
    citations: tuple[Citation, ...] = Field(min_length=1)


class Draft(BaseSchema):
    """What the writer proposes for a case.

    Facts and recommendations are kept apart: `assertions` are checkable statements,
    each with its sources, while `summary`, `correction` and `missing_evidence` say what
    to do and are for the human reviewer to judge.
    """

    action: RecommendedAction
    summary: str = Field(min_length=1)
    assertions: tuple[Assertion, ...] = ()
    correction: str | None = None
    missing_evidence: tuple[str, ...] = ()
