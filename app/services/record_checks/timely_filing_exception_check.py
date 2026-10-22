from datetime import date

from app.constants.record_checks import ACCEPTED_WORDING, REJECTED_WORDING
from app.interfaces.service.record_check import IRecordCheck
from app.schemas.finding import Finding, FindingCode
from app.schemas.payer_rule_set import PayerRuleSet
from app.schemas.record_check_context import RecordCheckContext
from app.schemas.supporting_document import DocumentKind, SupportingDocument


class TimelyFilingExceptionCheck(IRecordCheck):
    """Finds a document showing that a late claim falls under a filing-limit exception.

    It runs only when the rules found the claim past the ordinary limit, and reports one
    of the two exceptions a document can prove by its type and dates:

    - another payer was primary, and this claim was received within the payer's allowance
      after the date on that payer's explanation of benefits;
    - a clearinghouse or plan report, dated within the limit, records that the payer
      accepted the claim. A report that also records a rejection is not taken as proof,
      and the provider's own billing records are never proof.

    It reads the documents' types, dates and wording, never a model's summary of them.
    """

    def check(self, context: RecordCheckContext) -> tuple[Finding, ...]:
        if not context.has_finding(FindingCode.FILING_LIMIT_EXCEEDED):
            return ()
        rules = context.payer_rules
        claim = context.case_input.claim
        documents = context.case_input.supporting_documents

        for document in documents:
            finding = self._primary_payer(document, claim.submitted_date, rules)
            if finding is not None:
                return (finding,)
        service_date = max(line.service_date for line in claim.lines)
        for document in documents:
            finding = self._accepted_in_time(document, service_date, rules)
            if finding is not None:
                return (finding,)
        return ()

    @staticmethod
    def _primary_payer(
        document: SupportingDocument, received: date, rules: PayerRuleSet
    ) -> Finding | None:
        days_allowed = rules.primary_payer_filing_days
        if document.kind is not DocumentKind.PRIMARY_PAYER_EOB or days_allowed is None:
            return None
        days = (received - document.document_date).days
        if not 0 <= days <= days_allowed:
            return None
        clause_id = rules.primary_payer_filing_clause
        return Finding(
            code=FindingCode.TIMELY_FILING_EXCEPTION_DOCUMENTED,
            message=(
                f"{document.document_id} is the primary payer's explanation of benefits, "
                f"dated {document.document_date.isoformat()}. The claim was received {days} "
                f"days later, within the {days_allowed} days this payer allows after it."
            ),
            clause_ids=(clause_id,) if clause_id else (),
        )

    @staticmethod
    def _accepted_in_time(
        document: SupportingDocument, service_date: date, rules: PayerRuleSet
    ) -> Finding | None:
        if document.kind is not DocumentKind.CLEARINGHOUSE_REPORT:
            return None
        if not ACCEPTED_WORDING.search(document.text) or REJECTED_WORDING.search(document.text):
            return None
        limit = rules.filing_limit_days
        earlier = rules.earlier_filing_limit
        if earlier is not None and service_date < earlier.service_before:
            limit = earlier.days
        days = (document.document_date - service_date).days
        if not 0 <= days <= limit:
            return None
        clause_id = rules.filing_proof_clause
        return Finding(
            code=FindingCode.TIMELY_FILING_EXCEPTION_DOCUMENTED,
            message=(
                f"{document.document_id} is a clearinghouse report dated "
                f"{document.document_date.isoformat()}, {days} days after the service and "
                f"inside the {limit}-day limit, that records the payer's "
                "acceptance of the claim."
            ),
            clause_ids=(clause_id,) if clause_id else (),
        )
