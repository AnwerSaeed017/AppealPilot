from datetime import date
from enum import StrEnum
from typing import Self

from pydantic import Field, model_validator

from app.schemas.base_schema import BaseSchema
from app.schemas.claim import ClaimLine
from app.schemas.code_types import CarcCode, ClaimId


class PriorClaimOutcome(StrEnum):
    PAID = "PAID"
    DENIED = "DENIED"


class PriorClaim(BaseSchema):
    """An earlier claim for the same member and billing provider, already processed."""

    claim_id: ClaimId
    received_date: date
    outcome: PriorClaimOutcome
    # The reason for a denial, when the practice has it on file.
    carc_code: CarcCode | None = None
    lines: tuple[ClaimLine, ...] = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def _paid_has_no_reason(self) -> Self:
        if self.outcome is PriorClaimOutcome.PAID and self.carc_code is not None:
            raise ValueError("a paid claim has no denial reason")
        return self
