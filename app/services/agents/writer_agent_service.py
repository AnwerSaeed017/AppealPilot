from collections.abc import Sequence

from app.agents.prompts import writer_prompt
from app.constants.agents import MAX_OUTPUT_TOKENS, STEP_WRITER, WRITER_REASONING_EFFORT
from app.interfaces.service.structured_llm_service import IStructuredLlmService
from app.interfaces.service.writer_agent_service import IWriterAgentService
from app.interfaces.utilities.case_renderer import ICaseRenderer
from app.schemas.audit_event import AgentResult
from app.schemas.case_clause import CaseClause
from app.schemas.case_input import CaseInput
from app.schemas.draft import Draft
from app.schemas.finding import Finding
from app.schemas.note_fact import NoteFact
from app.schemas.triage_decision import TriageDecision
from app.schemas.verification_report import VerificationReport


class WriterAgentService(IWriterAgentService):
    def __init__(self, structured_llm: IStructuredLlmService, renderer: ICaseRenderer) -> None:
        self._structured_llm = structured_llm
        self._renderer = renderer

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
        return await self._structured_llm.complete(
            task=STEP_WRITER,
            prompt_version=writer_prompt.VERSION,
            system=writer_prompt.SYSTEM,
            user=user,
            output_type=Draft,
            max_output_tokens=MAX_OUTPUT_TOKENS[STEP_WRITER],
            reasoning_effort=WRITER_REASONING_EFFORT,
        )
