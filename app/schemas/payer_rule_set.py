from datetime import date

from pydantic import Field

from app.schemas.base_schema import BaseSchema
from app.schemas.code_types import ClauseId, PlaceOfServiceCode, ProcedureCode


class EarlierFilingLimit(BaseSchema):
    """A filing limit that still applies to services before a cut-off date."""

    service_before: date
    days: int = Field(gt=0)
    clause_id: ClauseId


class PayerRuleSet(BaseSchema):
    """The parts of a payer's policies that code can apply without judgement.

    Each limit or list sits next to the clause it comes from, so a finding can cite it.
    """

    filing_limit_days: int = Field(gt=0)
    filing_limit_clause: ClauseId
    earlier_filing_limit: EarlierFilingLimit | None = None

    corrected_claim_days: int = Field(gt=0)
    corrected_claim_clause: ClauseId
    appeal_days: int = Field(gt=0)
    appeal_clause: ClauseId

    authorization_codes: tuple[ProcedureCode, ...]
    authorization_clause: ClauseId
    authorization_number_clause: ClauseId
    authorization_exempt_places: tuple[PlaceOfServiceCode, ...] = ()
    authorization_exempt_clause: ClauseId | None = None

    side_modifier_codes: tuple[ProcedureCode, ...]
    side_modifier_clause: ClauseId
    modifier_25_clause: ClauseId

    repeat_modifier_clause: ClauseId
    duplicate_paid_clause: ClauseId
    duplicate_replacement_clause: ClauseId
    duplicate_denied_clause: ClauseId | None = None

    # The clause that says how a correction to a processed claim is submitted (for
    # Medicare, a reopening). Cited whenever a rule finds an error that can be corrected.
    correction_route_clause: ClauseId | None = None

    # For each procedure code, the clause that sets the conditions for paying it.
    procedure_clauses: dict[ProcedureCode, ClauseId] = Field(default_factory=dict)
