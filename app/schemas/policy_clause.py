from datetime import date
from typing import Self

from pydantic import Field, model_validator

from app.schemas.base_schema import BaseSchema
from app.schemas.code_types import ClauseId, PayerId, PolicyId, SourceUrl


class PolicyClause(BaseSchema):
    """One citable clause of a synthetic payer policy.

    The clause ID embeds the policy ID, which embeds the payer ID (ACME-PA-4.2 belongs
    to policy ACME-PA of payer ACME), so a citation can be checked by code.
    """

    clause_id: ClauseId
    policy_id: PolicyId
    payer_id: PayerId
    policy_title: str = Field(min_length=1, max_length=200)
    section_heading: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=4000)
    effective_from: date
    effective_to: date | None = None
    # Set when the clause is quoted from a published source rather than written for the
    # synthetic payers.
    source_url: SourceUrl | None = None

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        if not self.policy_id.startswith(f"{self.payer_id}-"):
            raise ValueError("policy_id must start with the payer_id")
        if not self.clause_id.startswith(f"{self.policy_id}-"):
            raise ValueError("clause_id must start with the policy_id")
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("effective_to must not be before effective_from")
        return self
