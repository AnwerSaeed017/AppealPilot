from collections.abc import Sequence
from datetime import date

from app.agents.prompts import triage_prompt
from app.constants.agents import MAX_OUTPUT_TOKENS, STEP_TRIAGE
from app.interfaces.service.structured_llm_service import IStructuredLlmService
from app.interfaces.service.triage_agent_service import ITriageAgentService
from app.interfaces.service.triage_guard import ITriageGuard
from app.interfaces.utilities.case_renderer import ICaseRenderer
from app.schemas.audit_event import AgentResult
from app.schemas.case_clause import CaseClause
from app.schemas.case_input import CaseInput
from app.schemas.finding import Finding
from app.schemas.note_fact import NoteFact
from app.schemas.triage_decision import TriageDecision


class TriageAgentService(ITriageAgentService):
    """Triage sees the extracted facts, not the raw documents.

    Only the intake step reads the documents directly, so text in a note cannot address
    the step that chooses the action.

    The model's choice is then checked by code against the findings (`ITriageGuard`): a
    choice that contradicts what code established is replaced, and the model's own
    choice and reasons are kept after the code's.
    """

    def __init__(
        self,
        structured_llm: IStructuredLlmService,
        renderer: ICaseRenderer,
        guards: Sequence[ITriageGuard],
    ) -> None:
        self._structured_llm = structured_llm
        self._renderer = renderer
        # In order of priority; the first guard that replaces the decision decides.
        self._guards = tuple(guards)

    async def decide(
        self,
        case_input: CaseInput,
        as_of: date,
        findings: Sequence[Finding],
        clauses: Sequence[CaseClause],
        note_facts: Sequence[NoteFact],
    ) -> AgentResult[TriageDecision]:
        result = await self._structured_llm.complete(
            task=STEP_TRIAGE,
            prompt_version=triage_prompt.VERSION,
            system=triage_prompt.SYSTEM,
            user=triage_prompt.USER.format(
                as_of=as_of.isoformat(),
                structured_data=self._renderer.structured_data(case_input),
                findings=self._renderer.findings(findings),
                clauses=self._renderer.clauses(clauses),
                note_facts=self._renderer.note_facts(note_facts),
            ),
            output_type=TriageDecision,
            max_output_tokens=MAX_OUTPUT_TOKENS[STEP_TRIAGE],
        )
        for guard in self._guards:
            replacement = guard.check(findings, result.output)
            if replacement is not None:
                return result.model_copy(update={"output": replacement})
        return result
