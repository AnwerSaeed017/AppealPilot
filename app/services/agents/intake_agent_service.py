from app.agents.prompts import intake_prompt
from app.constants.agents import MAX_OUTPUT_TOKENS, STEP_INTAKE
from app.interfaces.service.intake_agent_service import IIntakeAgentService
from app.interfaces.service.structured_llm_service import IStructuredLlmService
from app.interfaces.utilities.case_renderer import ICaseRenderer
from app.schemas.audit_event import AgentResult, LlmCallRecord
from app.schemas.case_input import CaseInput
from app.schemas.note_fact import NoteFact, NoteFacts


class IntakeAgentService(IIntakeAgentService):
    """Reads the record and extracts facts, each with the exact words it rests on.

    No supporting document is silently left unread. A model asked to read several
    documents sometimes takes facts from the visit note alone; when a supporting document
    yields no fact, it is read again on its own and its facts are added. The evidence an
    appeal needs is often in exactly those documents: a pharmacy history, a test report.
    """

    def __init__(self, structured_llm: IStructuredLlmService, renderer: ICaseRenderer) -> None:
        self._structured_llm = structured_llm
        self._renderer = renderer

    async def extract(self, case_input: CaseInput) -> AgentResult[NoteFacts]:
        first = await self._read(
            case_input, intake_prompt.VERSION, intake_prompt.USER, document_ids=None
        )
        facts = first.output.facts
        read = {fact.document_id for fact in facts}
        unread = tuple(
            document
            for document in case_input.supporting_documents
            if document.document_id not in read
        )
        if not unread:
            return first

        ids = tuple(document.document_id for document in unread)
        second = await self._read(
            case_input.model_copy(update={"supporting_documents": unread}),
            intake_prompt.UNREAD_VERSION,
            intake_prompt.UNREAD_USER,
            document_ids=ids,
        )
        # Only facts from the documents read again are taken; the rest are known.
        added = tuple(fact for fact in second.output.facts if fact.document_id in ids)
        return AgentResult(
            output=NoteFacts(facts=(*facts, *added)),
            llm_call=_combined(first.llm_call, second.llm_call),
        )

    async def _read(
        self,
        case_input: CaseInput,
        prompt_version: str,
        user: str,
        document_ids: tuple[str, ...] | None,
    ) -> AgentResult[NoteFacts]:
        result = await self._structured_llm.complete(
            task=STEP_INTAKE,
            prompt_version=prompt_version,
            system=intake_prompt.SYSTEM,
            user=user.format(
                structured_data=self._renderer.structured_data(case_input),
                documents=self._renderer.documents(case_input),
                document_ids=", ".join(document_ids or ()),
            ),
            output_type=NoteFacts,
            max_output_tokens=MAX_OUTPUT_TOKENS[STEP_INTAKE],
        )
        return result.model_copy(update={"output": NoteFacts(facts=self._clean(result.output))})

    def _clean(self, facts: NoteFacts) -> tuple[NoteFact, ...]:
        """Line numbers copied from the rendered documents are not part of a quote."""
        return tuple(
            fact.model_copy(update={"quote": self._renderer.without_line_numbers(fact.quote)})
            for fact in facts.facts
        )


def _combined(first: LlmCallRecord, second: LlmCallRecord) -> LlmCallRecord:
    """The cost of a step that asked the model twice."""
    return first.model_copy(
        update={
            "input_tokens": first.input_tokens + second.input_tokens,
            "output_tokens": first.output_tokens + second.output_tokens,
            "latency_ms": first.latency_ms + second.latency_ms,
            "cached": first.cached and second.cached,
            "attempts": first.attempts + second.attempts,
        }
    )
