from collections.abc import Sequence

from app.constants.text import PASSAGE_BREAK
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
            return self._why_not_found(citation, source)
        return None

    def _why_not_found(self, citation: Citation, source: str) -> str:
        """Says why a quote is not in its source, so a rewrite can fix the right thing.

        A quote built from passages that are each in the source, but not next to each
        other, is the commonest case: a model shortened it with "..." or joined two
        sentences. Saying so tells the writer to cite each passage on its own.
        """
        missing = f'the quote "{citation.quote}" is not in {citation.source_id}'
        passages = [part for part in PASSAGE_BREAK.split(citation.quote) if part.strip()]
        if len(passages) > 1 and all(
            self._quote_matcher.contains(source, passage) for passage in passages
        ):
            return (
                f"{missing}: it joins passages that are not next to each other in the "
                "source, or shortens one with an ellipsis. Quote each passage as it "
                "stands, in its own citation."
            )
        return missing
