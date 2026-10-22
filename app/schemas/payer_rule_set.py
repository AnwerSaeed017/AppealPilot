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
    # What follows when the record does not support modifier 25, and how a missing side
    # is corrected. Cited with the finding that raises the question.
    modifier_25_unsupported_clause: ClauseId | None = None
    side_modifier_fix_clauses: tuple[ClauseId, ...] = ()

    repeat_modifier_clause: ClauseId
    duplicate_paid_clause: ClauseId
    duplicate_replacement_clause: ClauseId
    duplicate_denied_clause: ClauseId | None = None

    # The clause that says how a correction to a processed claim is submitted (for
    # Medicare, a reopening). Cited whenever a rule finds an error that can be corrected.
    correction_route_clause: ClauseId | None = None

    # Days a claim has after the date on the primary payer's explanation of benefits,
    # when another payer was billed first, and the clause that allows it.
    primary_payer_filing_days: int | None = Field(default=None, gt=0)
    primary_payer_filing_clause: ClauseId | None = None
    # The clause that names what proves a claim was filed on time.
    filing_proof_clause: ClauseId | None = None
    # The clause on entries added to the record later, cited when an addendum is dated
    # after the denial.
    late_entry_clause: ClauseId | None = None
    # For each denial reason code, the clauses that say what follows from that denial:
    # whether it is final, how it is appealed or corrected, what exceptions apply. The
    # denial's wording matches the clause that states a requirement, not the one that
    # says what to do about it, so the rules name these instead of leaving them to search.
    denial_response_clauses: dict[str, tuple[ClauseId, ...]] = Field(default_factory=dict)
    # For each procedure code, the clause that sets the conditions for paying it.
    procedure_clauses: dict[ProcedureCode, ClauseId] = Field(default_factory=dict)
