from collections.abc import Sequence

from app.core.exceptions import ValidationFailedError
from app.interfaces.repository.policy_repository import IPolicyRepository
from app.interfaces.service.record_check import IRecordCheck
from app.interfaces.service.record_check_service import IRecordCheckService
from app.interfaces.utilities.quote_matcher import IQuoteMatcher
from app.schemas.case_input import CaseInput
from app.schemas.finding import Finding
from app.schemas.note_fact import NoteFact
from app.schemas.record_check_context import RecordCheckContext


class RecordCheckService(IRecordCheckService):
    """Runs the record checks on the facts that are really in the documents.

    A fact whose quote is not found in its document is set aside: the checks act only on
    words the record contains, never on words a model supplied.
    """

    def __init__(
        self,
        checks: Sequence[IRecordCheck],
        quote_matcher: IQuoteMatcher,
        policy_repository: IPolicyRepository,
    ) -> None:
        self._checks = tuple(checks)
        self._quote_matcher = quote_matcher
        self._policy_repository = policy_repository

    async def check(
        self, case_input: CaseInput, facts: Sequence[NoteFact], findings: Sequence[Finding]
    ) -> tuple[Finding, ...]:
        payer = await self._policy_repository.get_payer(case_input.claim.payer_id)
        if payer is None:
            raise ValidationFailedError(f"Unknown payer {case_input.claim.payer_id}.")
        context = RecordCheckContext(
            case_input=case_input,
            payer_rules=payer.rules,
            facts=tuple(fact for fact in facts if self._is_in_record(case_input, fact)),
            findings=tuple(findings),
        )
        return tuple(finding for check in self._checks for finding in check.check(context))

    def _is_in_record(self, case_input: CaseInput, fact: NoteFact) -> bool:
        source = case_input.document_text(fact.document_id)
        return source is not None and self._quote_matcher.contains(source, fact.quote)
