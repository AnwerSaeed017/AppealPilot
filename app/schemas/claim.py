from datetime import date
from decimal import Decimal
from typing import Annotated, Self

from pydantic import Field, model_validator

from app.schemas.base_schema import BaseSchema
from app.schemas.code_types import (
    ClaimId,
    IcdCode,
    LineNumber,
    MemberId,
    ModifierCode,
    Money,
    Npi,
    PatientId,
    PayerId,
    PlaceOfServiceCode,
    PriorAuthorizationNumber,
    ProcedureCode,
)

_MAX_DIAGNOSES = 12

DiagnosisPointer = Annotated[int, Field(ge=1, le=_MAX_DIAGNOSES)]


class ClaimLine(BaseSchema):
    """One billed service."""

    line_number: LineNumber
    service_date: date
    procedure_code: ProcedureCode
    modifiers: tuple[ModifierCode, ...] = Field(default=(), max_length=4)
    # 1-based positions in the claim's diagnosis list, most relevant first.
    diagnosis_pointers: tuple[DiagnosisPointer, ...] = Field(min_length=1, max_length=4)
    units: int = Field(ge=1, le=999)
    charge_amount: Money

    @model_validator(mode="after")
    def _no_repeats(self) -> Self:
        if len(set(self.modifiers)) != len(self.modifiers):
            raise ValueError("modifiers must not repeat")
        if len(set(self.diagnosis_pointers)) != len(self.diagnosis_pointers):
            raise ValueError("diagnosis_pointers must not repeat")
        return self


class Claim(BaseSchema):
    """A professional claim as submitted to the payer. Synthetic data only."""

    claim_id: ClaimId
    payer_id: PayerId
    member_id: MemberId
    patient_id: PatientId
    patient_date_of_birth: date
    billing_provider_npi: Npi
    place_of_service: PlaceOfServiceCode
    submitted_date: date
    prior_authorization_number: PriorAuthorizationNumber | None = None
    # Set when this claim replaces or repeats an earlier one.
    original_claim_id: ClaimId | None = None
    # The first diagnosis is the principal one.
    diagnosis_codes: tuple[IcdCode, ...] = Field(min_length=1, max_length=_MAX_DIAGNOSES)
    lines: tuple[ClaimLine, ...] = Field(min_length=1, max_length=50)
    total_charge: Money

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        if len(set(self.diagnosis_codes)) != len(self.diagnosis_codes):
            raise ValueError("diagnosis_codes must not repeat")

        line_numbers = [line.line_number for line in self.lines]
        if len(set(line_numbers)) != len(line_numbers):
            raise ValueError("line numbers must be unique")

        for line in self.lines:
            if max(line.diagnosis_pointers) > len(self.diagnosis_codes):
                raise ValueError(
                    f"line {line.line_number} points to a diagnosis that is not on the claim"
                )

        line_total = sum((line.charge_amount for line in self.lines), Decimal(0))
        if line_total != self.total_charge:
            raise ValueError("total_charge must equal the sum of the line charges")

        service_dates = [line.service_date for line in self.lines]
        if self.submitted_date < max(service_dates):
            raise ValueError("submitted_date must not be before a service date")
        if self.patient_date_of_birth > min(service_dates):
            raise ValueError("patient_date_of_birth must not be after a service date")

        if self.original_claim_id == self.claim_id:
            raise ValueError("original_claim_id must refer to a different claim")
        return self
