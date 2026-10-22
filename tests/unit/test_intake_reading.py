"""Record review leaves no supporting document unread."""

from typing import Any

from app.agents.prompts import intake_prompt
from app.schemas.audit_event import AgentResult, LlmCallRecord
from app.schemas.case_input import CaseInput
from app.schemas.note_fact import NoteFact, NoteFacts
from app.services.agents.intake_agent_service import IntakeAgentService
from app.utilities.case_renderer import CaseRenderer
from tests.samples import case_input_payload


def case_with_documents(*document_ids: str) -> CaseInput:
    payload = case_input_payload()
    payload["supporting_documents"] = [
        {
            "document_id": document_id,
            "kind": "OTHER",
            "document_date": payload["visit_note"]["encounter_date"],
            "text": f"{document_id} line one.",
        }
        for document_id in document_ids
    ]
    return CaseInput.model_validate(payload)


def fact(document_id: str) -> NoteFact:
    return NoteFact(
        statement=f"From {document_id}.",
        document_id=document_id,
        line_number=1,
        quote=f"{document_id} line one." if document_id != "NOTE" else "Established patient",
    )


class ScriptedModel:
    """Answers each call with the next set of facts, and records what it was asked."""

    def __init__(self, *answers: list[NoteFact]) -> None:
        self._answers = list(answers)
        self.calls: list[dict[str, Any]] = []

    async def complete(self, **request: Any) -> AgentResult[NoteFacts]:
        self.calls.append(request)
        call = LlmCallRecord(
            provider="mock",
            model="mock",
            input_tokens=100,
            output_tokens=10,
            latency_ms=5.0,
            cached=False,
            attempts=1,
        )
        return AgentResult(output=NoteFacts(facts=tuple(self._answers.pop(0))), llm_call=call)


async def test_a_document_that_yielded_no_fact_is_read_again_on_its_own() -> None:
    model = ScriptedModel(
        [fact("NOTE")],
        # The second answer also repeats a note fact, which must not be added twice.
        [fact("RX"), fact("NOTE")],
    )
    intake = IntakeAgentService(model, CaseRenderer())  # type: ignore[arg-type]

    result = await intake.extract(case_with_documents("RX"))

    assert [f.document_id for f in result.output.facts] == ["NOTE", "RX"]
    assert len(model.calls) == 2
    second = model.calls[1]
    assert second["prompt_version"] == intake_prompt.UNREAD_VERSION
    assert "these documents in\nfull" in second["user"]
    assert ": RX." in second["user"]
    # Both calls are counted in what the step cost.
    assert result.llm_call.attempts == 2
    assert result.llm_call.input_tokens == 200


async def test_when_every_document_yielded_facts_the_model_is_asked_once() -> None:
    model = ScriptedModel([fact("NOTE"), fact("RX")])
    intake = IntakeAgentService(model, CaseRenderer())  # type: ignore[arg-type]

    result = await intake.extract(case_with_documents("RX"))

    assert len(model.calls) == 1
    assert [f.document_id for f in result.output.facts] == ["NOTE", "RX"]


async def test_the_first_reading_is_the_unchanged_prompt() -> None:
    model = ScriptedModel([fact("NOTE")])
    intake = IntakeAgentService(model, CaseRenderer())  # type: ignore[arg-type]

    await intake.extract(case_with_documents())

    assert model.calls[0]["prompt_version"] == intake_prompt.VERSION
    assert "The facts already taken" not in model.calls[0]["user"]
