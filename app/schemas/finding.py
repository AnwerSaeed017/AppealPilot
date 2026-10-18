from enum import StrEnum

from pydantic import Field

from app.schemas.base_schema import BaseSchema
from app.schemas.code_types import ClauseId, LineNumber


class FindingCode(StrEnum):
    """Facts the rules engine can establish from the structured data alone."""

    FILING_LIMIT_EXCEEDED = "FILING_LIMIT_EXCEEDED"
    FILED_WITHIN_LIMIT = "FILED_WITHIN_LIMIT"
    CORRECTED_CLAIM_WINDOW_CLOSED = "CORRECTED_CLAIM_WINDOW_CLOSED"
    APPEAL_WINDOW_CLOSED = "APPEAL_WINDOW_CLOSED"
    DUPLICATE_OF_PAID_CLAIM = "DUPLICATE_OF_PAID_CLAIM"
    DUPLICATE_OF_DENIED_CLAIM = "DUPLICATE_OF_DENIED_CLAIM"
    CHANGED_VERSION_OF_PRIOR_CLAIM = "CHANGED_VERSION_OF_PRIOR_CLAIM"
    NO_MATCHING_PRIOR_CLAIM = "NO_MATCHING_PRIOR_CLAIM"
    REPEATED_LINE_WITHOUT_REPEAT_MODIFIER = "REPEATED_LINE_WITHOUT_REPEAT_MODIFIER"
    AUTHORIZATION_NUMBER_MISSING = "AUTHORIZATION_NUMBER_MISSING"
    AUTHORIZATION_NOT_REQUIRED = "AUTHORIZATION_NOT_REQUIRED"
    SIDE_MODIFIER_MISSING = "SIDE_MODIFIER_MISSING"
    VISIT_WITHOUT_MODIFIER_25 = "VISIT_WITHOUT_MODIFIER_25"
    NOTE_DATE_MISMATCH = "NOTE_DATE_MISMATCH"
    # Names the clause that sets the conditions for a denied procedure.
    PROCEDURE_CONDITIONS_CLAUSE = "PROCEDURE_CONDITIONS_CLAUSE"
    # Names the clause that says how the payer takes a correction to a processed claim.
    CORRECTION_ROUTE_CLAUSE = "CORRECTION_ROUTE_CLAUSE"
    # Found by code in the extracted facts, after the record has been read. Each one means
    # a person must decide: the workflow escalates whatever triage would have chosen.
    LATERALITY_CONTRADICTION = "LATERALITY_CONTRADICTION"
    DOCUMENT_PATIENT_MISMATCH = "DOCUMENT_PATIENT_MISMATCH"
    # Raised for denials that turn on clinical support, which no rule decides.
    CLINICAL_SUPPORT_NEEDS_REVIEW = "CLINICAL_SUPPORT_NEEDS_REVIEW"


class Finding(BaseSchema):
    """One fact about a case, with the clause it rests on where there is one.

    A finding states what is true of the data. It never recommends an action.
    """

    code: FindingCode
    message: str = Field(min_length=1)
    clause_ids: tuple[ClauseId, ...] = ()
    line_numbers: tuple[LineNumber, ...] = ()
