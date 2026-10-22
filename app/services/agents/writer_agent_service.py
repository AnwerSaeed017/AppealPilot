from collections.abc import Sequence

from app.agents.prompts import writer_prompt
from app.constants.agents import (
    MAX_OUTPUT_TOKENS,
    MIN_WORDS_IN_SPLIT_PASSAGE,
    STEP_WRITER,
    WRITER_REASONING_EFFORT,
)
from app.constants.text import PASSAGE_BREAK
from app.interfaces.service.structured_llm_service import IStructuredLlmService
from app.interfaces.service.writer_agent_service import IWriterAgentService
from app.interfaces.utilities.case_renderer import ICaseRenderer
from app.interfaces.utilities.quote_matcher import IQuoteMatcher
from app.schemas.audit_event import AgentResult
from app.schemas.case_clause import CaseClause
from app.schemas.case_input import CaseInput
from app.schemas.draft import Citation, CitationKind, Draft
from app.schemas.finding import Finding
from app.schemas.note_fact import NoteFact
from app.schemas.triage_decision import TriageDecision
from app.schemas.verification_report import VerificationReport


class WriterAgentService(IWriterAgentService):
    def __init__(
        self,
        structured_llm: IStructuredLlmService,
        renderer: ICaseRenderer,
        quote_matcher: IQuoteMatcher,
    ) -> None:
        self._structured_llm = structured_llm
        self._renderer = renderer
        self._quote_matcher = quote_matcher

    async def draft(
        self,
        case_input: CaseInput,
        findings: Sequence[Finding],
        clauses: Sequence[CaseClause],
        note_facts: Sequence[NoteFact],
        triage: TriageDecision,
        previous: Draft | None,
        feedback: VerificationReport | None,
    ) -> AgentResult[Draft]:
        user = writer_prompt.USER.format(
            action=triage.action.value,
            reasons="\n".join(f"- {reason}" for reason in triage.reasons),
            structured_data=self._renderer.structured_data(case_input),
            findings=self._renderer.findings(findings),
            clauses=self._renderer.clauses(clauses),
            note_facts=self._renderer.fact_pointers(note_facts),
            documents=self._renderer.documents(case_input),
        )
        if previous is not None and feedback is not None:
            user += writer_prompt.REVISION.format(
                previous=previous.model_dump_json(indent=2),
                problems="\n".join(
                    f"- assertion {verdict.assertion_index}: {'; '.join(verdict.problems)}"
                    for verdict in feedback.failures()
                ),
            )
        result = await self._structured_llm.complete(
            task=STEP_WRITER,
            prompt_version=writer_prompt.VERSION,
            system=writer_prompt.SYSTEM,
            user=user,
            output_type=Draft,
            max_output_tokens=MAX_OUTPUT_TOKENS[STEP_WRITER],
            reasoning_effort=WRITER_REASONING_EFFORT,
        )
        return result.model_copy(
            update={"output": self._clean_quotes(result.output, case_input, clauses)}
        )

    def _clean_quotes(
        self, draft: Draft, case_input: CaseInput, clauses: Sequence[CaseClause]
    ) -> Draft:
        """Repairs quotes whose words are all in the source but not as one passage.

        Line numbers copied from the rendered documents are removed. A quote that is not
        in its source as a whole, but whose passages each are, word for word, is split
        into one citation per passage: a model often joins two sentences or shortens one
        with "...". Nothing is invented by the split, and the judge still decides whether
        the passages support the assertion. A quote with any words not in the source is
        left as written, for the verifier to reject.
        """
        clause_texts = {item.clause.clause_id: item.clause.text for item in clauses}
        assertions = tuple(
            assertion.model_copy(
                update={
                    "citations": tuple(
                        repaired
                        for citation in assertion.citations
                        for repaired in self._repaired(citation, case_input, clause_texts)
                    )
                }
            )
            for assertion in draft.assertions
        )
        return draft.model_copy(update={"assertions": assertions})

    def _repaired(
        self, citation: Citation, case_input: CaseInput, clause_texts: dict[str, str]
    ) -> tuple[Citation, ...]:
        if citation.kind is CitationKind.DOCUMENT:
            citation = citation.model_copy(
                update={"quote": self._renderer.without_line_numbers(citation.quote)}
            )
            source = case_input.document_text(citation.source_id)
        else:
            source = clause_texts.get(citation.source_id)
        if source is None or self._quote_matcher.contains(source, citation.quote):
            return (citation,)
        passages = [
            passage.strip()
            for passage in PASSAGE_BREAK.split(citation.quote)
            if len(passage.split()) >= MIN_WORDS_IN_SPLIT_PASSAGE
        ]
        if len(passages) < 2 or not all(
            self._quote_matcher.contains(source, passage) for passage in passages
        ):
            return (citation,)
        return tuple(citation.model_copy(update={"quote": passage}) for passage in passages)
