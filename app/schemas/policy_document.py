from datetime import date
from typing import Self

from pydantic import Field, model_validator

from app.schemas.base_schema import BaseSchema
from app.schemas.code_types import ClauseId, PayerId, PolicyId, SourceUrl
from app.schemas.policy_clause import PolicyClause


class PolicyDocumentClause(BaseSchema):
    clause_id: ClauseId
    section_heading: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=4000)
    source_url: SourceUrl | None = None


class PolicyDocument(BaseSchema):
    """One policy file: shared details once, then its clauses."""

    policy_id: PolicyId
    payer_id: PayerId
    title: str = Field(min_length=1, max_length=200)
    effective_from: date
    effective_to: date | None = None
    clauses: tuple[PolicyDocumentClause, ...] = Field(min_length=1)

    def to_clauses(self) -> tuple[PolicyClause, ...]:
        """The clauses as standalone, citable records."""
        return tuple(
            PolicyClause(
                clause_id=clause.clause_id,
                policy_id=self.policy_id,
                payer_id=self.payer_id,
                policy_title=self.title,
                section_heading=clause.section_heading,
                text=clause.text,
                effective_from=self.effective_from,
                effective_to=self.effective_to,
                source_url=clause.source_url,
            )
            for clause in self.clauses
        )

    @model_validator(mode="after")
    def _check_clauses(self) -> Self:
        clause_ids = [clause.clause_id for clause in self.clauses]
        if len(set(clause_ids)) != len(clause_ids):
            raise ValueError("clause IDs must be unique within a policy")
        # Building the standalone clauses applies the ID and date rules of PolicyClause.
        self.to_clauses()
        return self
