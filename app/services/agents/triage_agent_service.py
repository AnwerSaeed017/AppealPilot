from collections.abc import Sequence
from datetime import date

from app.agents.prompts import triage_prompt
from app.constants.agents import MAX_OUTPUT_TOKENS, STEP_TRIAGE
from app.constants.findings import ESCALATION_FINDINGS
from app.interfaces.service.structured_llm_service import IStructuredLlmService
from app.interfaces.service.triage_agent_service import ITriageAgentService
from app.interfaces.utilities.case_renderer import ICaseRenderer
from app.schemas.audit_event import AgentResult
from app.schemas.case_clause import CaseClause
from app.schemas.case_input import CaseInput
from app.schemas.finding import Finding
from app.schemas.note_fact import NoteFact
from app.schemas.recommended_action import RecommendedAction
from app.schemas.triage_decision import TriageDecision


class TriageAgentService(ITriageAgentService):
    """Triage sees the extracted facts, not the raw documents.

    Only the intake step reads the documents directly, so text in a note cannot address
    the step that chooses the action.

    A finding in `ESCALATION_FINDINGS` sends the case to a person whatever the model
    chose: those are established by code, and a model has been seen to argue its way
    past a contradiction it was shown.
    """

    def __init__(self, structured_llm: IStructuredLlmService, renderer: ICaseRenderer) -> None:
        self._structured_llm = structured_llm
        self._renderer = renderer

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
        blocking = [finding for finding in findings if finding.code in ESCALATION_FINDINGS]
        if not blocking or result.output.action is RecommendedAction.ESCALATE_TO_HUMAN:
            return result
        reasons = tuple(
            f"Escalated by code: {finding.code.value}. {finding.message}" for finding in blocking
        )
        return result.model_copy(
            update={
                "output": TriageDecision(
                    action=RecommendedAction.ESCALATE_TO_HUMAN,
                    confidence=result.output.confidence,
                    reasons=(
                        *reasons,
                        f"The model had chosen {result.output.action.value}:",
                        *result.output.reasons,
                    ),
                )
            }
        )
