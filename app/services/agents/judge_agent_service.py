import json
from collections.abc import Sequence

from app.agents.prompts import judge_prompt
from app.constants.agents import MAX_OUTPUT_TOKENS, TASK_JUDGE
from app.interfaces.service.judge_agent_service import IJudgeAgentService
from app.interfaces.service.structured_llm_service import IStructuredLlmService
from app.interfaces.utilities.case_renderer import ICaseRenderer
from app.schemas.audit_event import AgentResult
from app.schemas.case_clause import CaseClause
from app.schemas.case_input import CaseInput
from app.schemas.draft import Draft
from app.schemas.verification_report import JudgeVerdicts


class JudgeAgentService(IJudgeAgentService):
    """Asks a second model whether each assertion follows from what it quotes.

    It is built on the judge model, which comes from a different provider than the
    writer's, so a model is never the only check on its own output.
    """

    def __init__(self, structured_llm: IStructuredLlmService, renderer: ICaseRenderer) -> None:
        self._structured_llm = structured_llm
        self._renderer = renderer

    async def judge(
        self,
        draft: Draft,
        assertion_indexes: Sequence[int],
        case_input: CaseInput,
        clauses: Sequence[CaseClause],
    ) -> AgentResult[JudgeVerdicts]:
        assertions = [
            {"assertion_index": index, **draft.assertions[index].model_dump(mode="json")}
            for index in assertion_indexes
        ]
        return await self._structured_llm.complete(
            task=TASK_JUDGE,
            prompt_version=judge_prompt.VERSION,
            system=judge_prompt.SYSTEM,
            user=judge_prompt.USER.format(
                clauses=self._renderer.clauses(clauses),
                documents=self._renderer.documents(case_input),
                assertions=json.dumps(assertions, indent=2),
            ),
            output_type=JudgeVerdicts,
            max_output_tokens=MAX_OUTPUT_TOKENS[TASK_JUDGE],
        )
