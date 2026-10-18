from collections.abc import Sequence

from app.interfaces.service.citation_check_service import ICitationCheckService
from app.interfaces.utilities.quote_matcher import IQuoteMatcher
from app.schemas.case_clause import CaseClause
from app.schemas.case_input import CaseInput
from app.schemas.draft import Citation, CitationKind, Draft
from app.schemas.verification_report import AssertionVerdict, VerificationReport


class CitationVerifierService(ICitationCheckService):
    """Checks citations by code: the source exists, was selected for this case, and
    really contains the words quoted.

    This catches invented clause IDs, clauses borrowed from outside the case, and quotes
    that are not in the source. It does not judge whether a real quote supports the
    assertion made from it; that is the model judge's job, which runs after this one.
    """

    def __init__(self, quote_matcher: IQuoteMatcher) -> None:
        self._quote_matcher = quote_matcher

    def check(
        self, draft: Draft, case_input: CaseInput, clauses: Sequence[CaseClause]
    ) -> VerificationReport:
        clause_texts = {item.clause.clause_id: item.clause.text for item in clauses}
        verdicts: list[AssertionVerdict] = []
        for index, assertion in enumerate(draft.assertions):
            problems = [
                problem
                for citation in assertion.citations
                if (problem := self._problem(citation, case_input, clause_texts)) is not None
            ]
            verdicts.append(
                AssertionVerdict(
                    assertion_index=index, supported=not problems, problems=tuple(problems)
                )
            )
        return VerificationReport(verdicts=tuple(verdicts))

    def _problem(
        self, citation: Citation, case_input: CaseInput, clause_texts: dict[str, str]
    ) -> str | None:
        if citation.kind is CitationKind.CLAUSE:
            source = clause_texts.get(citation.source_id)
            if source is None:
                return f"clause {citation.source_id} was not selected for this case"
        else:
            source = case_input.document_text(citation.source_id)
            if source is None:
                return f"document {citation.source_id} is not part of this case"

        if not self._quote_matcher.contains(source, citation.quote):
            return f'the quote "{citation.quote}" is not in {citation.source_id}'
        return None
