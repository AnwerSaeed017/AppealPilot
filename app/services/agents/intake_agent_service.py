from app.agents.prompts import intake_prompt
from app.constants.agents import MAX_OUTPUT_TOKENS, STEP_INTAKE
from app.interfaces.service.intake_agent_service import IIntakeAgentService
from app.interfaces.service.structured_llm_service import IStructuredLlmService
from app.interfaces.utilities.case_renderer import ICaseRenderer
from app.schemas.audit_event import AgentResult
from app.schemas.case_input import CaseInput
from app.schemas.note_fact import NoteFacts


class IntakeAgentService(IIntakeAgentService):
    def __init__(self, structured_llm: IStructuredLlmService, renderer: ICaseRenderer) -> None:
        self._structured_llm = structured_llm
        self._renderer = renderer

    async def extract(self, case_input: CaseInput) -> AgentResult[NoteFacts]:
        return await self._structured_llm.complete(
            task=STEP_INTAKE,
            prompt_version=intake_prompt.VERSION,
            system=intake_prompt.SYSTEM,
            user=intake_prompt.USER.format(
                structured_data=self._renderer.structured_data(case_input),
                documents=self._renderer.documents(case_input),
            ),
            output_type=NoteFacts,
            max_output_tokens=MAX_OUTPUT_TOKENS[STEP_INTAKE],
        )
