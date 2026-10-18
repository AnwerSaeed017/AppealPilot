from typing import Self

from pydantic import Field, model_validator

from app.schemas.base_schema import BaseSchema
from app.schemas.claim import Claim
from app.schemas.code_types import VISIT_NOTE_DOCUMENT_ID
from app.schemas.denial import Denial
from app.schemas.prior_claim import PriorClaim
from app.schemas.supporting_document import SupportingDocument
from app.schemas.visit_note import VisitNote


class CaseInput(BaseSchema):
    """Everything a billing user submits for one denied claim."""

    claim: Claim
    denial: Denial
    visit_note: VisitNote
    supporting_documents: tuple[SupportingDocument, ...] = Field(default=(), max_length=8)
    prior_claims: tuple[PriorClaim, ...] = Field(default=(), max_length=10)

    @model_validator(mode="after")
    def _denial_matches_claim(self) -> Self:
        if self.denial.claim_id != self.claim.claim_id:
            raise ValueError("the denial refers to a different claim")
        if self.denial.payer_id != self.claim.payer_id:
            raise ValueError("the denial comes from a different payer than the claim")

        claim_lines = {line.line_number for line in self.claim.lines}
        unknown = sorted(set(self.denial.denied_line_numbers) - claim_lines)
        if unknown:
            raise ValueError(f"the denial names lines that are not on the claim: {unknown}")

        if self.denial.denial_date < self.claim.submitted_date:
            raise ValueError("denial_date must not be before the claim was submitted")
        if self.denial.denied_amount > self.claim.total_charge:
            raise ValueError("denied_amount must not exceed the claim's total_charge")
        return self

    @model_validator(mode="after")
    def _references_are_unambiguous(self) -> Self:
        document_ids = [document.document_id for document in self.supporting_documents]
        if VISIT_NOTE_DOCUMENT_ID in document_ids:
            raise ValueError(f"{VISIT_NOTE_DOCUMENT_ID} is reserved for the visit note")
        if len(set(document_ids)) != len(document_ids):
            raise ValueError("supporting document IDs must be unique")

        prior_ids = [prior.claim_id for prior in self.prior_claims]
        if self.claim.claim_id in prior_ids:
            raise ValueError("a prior claim must not have the same ID as the claim")
        if len(set(prior_ids)) != len(prior_ids):
            raise ValueError("prior claim IDs must be unique")
        return self

    def document_text(self, document_id: str) -> str | None:
        """The text a citation to `document_id` refers to, or None if there is none."""
        if document_id == VISIT_NOTE_DOCUMENT_ID:
            return self.visit_note.text
        for document in self.supporting_documents:
            if document.document_id == document_id:
                return document.text
        return None
