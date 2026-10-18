from collections.abc import Sequence

from app.interfaces.service.record_check import IRecordCheck
from app.interfaces.service.record_check_service import IRecordCheckService
from app.interfaces.utilities.quote_matcher import IQuoteMatcher
from app.schemas.case_input import CaseInput
from app.schemas.finding import Finding
from app.schemas.note_fact import NoteFact


class RecordCheckService(IRecordCheckService):
    """Runs the record checks on the facts that are really in the documents.

    A fact whose quote is not found in its document is set aside: the checks act only on
    words the record contains, never on words a model supplied.
    """

    def __init__(self, checks: Sequence[IRecordCheck], quote_matcher: IQuoteMatcher) -> None:
        self._checks = tuple(checks)
        self._quote_matcher = quote_matcher

    def check(self, case_input: CaseInput, facts: Sequence[NoteFact]) -> tuple[Finding, ...]:
        verified = [fact for fact in facts if self._is_in_record(case_input, fact)]
        return tuple(
            finding for check in self._checks for finding in check.check(case_input, verified)
        )

    def _is_in_record(self, case_input: CaseInput, fact: NoteFact) -> bool:
        source = case_input.document_text(fact.document_id)
        return source is not None and self._quote_matcher.contains(source, fact.quote)
