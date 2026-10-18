from datetime import date
from enum import StrEnum
from typing import Self

from pydantic import Field, model_validator

from app.schemas.base_schema import BaseSchema
from app.schemas.code_types import CarcCode, ClaimId, LineNumber, Money, PayerId, RarcCode


class ClaimAdjustmentGroup(StrEnum):
    """Who is financially responsible for the adjusted amount."""

    CONTRACTUAL_OBLIGATION = "CO"
    PATIENT_RESPONSIBILITY = "PR"
    OTHER_ADJUSTMENT = "OA"
    PAYER_INITIATED = "PI"


class Denial(BaseSchema):
    """The payer's decision on a claim, as reported on a remittance advice."""

    claim_id: ClaimId
    payer_id: PayerId
    group_code: ClaimAdjustmentGroup
    carc_code: CarcCode
    rarc_codes: tuple[RarcCode, ...] = Field(default=(), max_length=5)
    denial_date: date
    # Empty means the whole claim was denied.
    denied_line_numbers: tuple[LineNumber, ...] = ()
    denied_amount: Money
    payer_remark: str | None = Field(default=None, min_length=1, max_length=2000)

    @model_validator(mode="after")
    def _no_repeats(self) -> Self:
        if len(set(self.rarc_codes)) != len(self.rarc_codes):
            raise ValueError("rarc_codes must not repeat")
        if len(set(self.denied_line_numbers)) != len(self.denied_line_numbers):
            raise ValueError("denied_line_numbers must not repeat")
        return self
