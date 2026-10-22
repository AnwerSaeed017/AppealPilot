"""The writer's repair of quotes: only what is word for word in the source survives."""

from typing import Any

from app.schemas.audit_event import AgentResult, LlmCallRecord
from app.schemas.case_clause import CaseClause, ClauseOrigin
from app.schemas.case_input import CaseInput
from app.schemas.draft import Draft
from app.schemas.policy_clause import PolicyClause
from app.schemas.recommended_action import RecommendedAction
from app.schemas.triage_decision import TriageDecision
from app.services.agents.writer_agent_service import WriterAgentService
from app.utilities.case_renderer import CaseRenderer
from app.utilities.quote_matcher import QuoteMatcher
from tests.samples import case_input_payload, policy_clause_payload

CASE = CaseInput.model_validate(case_input_payload())
CLAUSE = PolicyClause.model_validate(policy_clause_payload())
CLAUSES = [CaseClause(clause=CLAUSE, rank=1, origin=ClauseOrigin.SEARCH)]
TRIAGE = TriageDecision(
    action=RecommendedAction.APPEAL_WITH_EVIDENCE, confidence=0.9, reasons=("reason",)
)


class FixedDraft:
    """Stands in for the structured model call and returns one draft."""

    def __init__(self, citations: list[dict[str, Any]]) -> None:
        self._draft = Draft.model_validate(
            {
                "action": "APPEAL_WITH_EVIDENCE",
                "summary": "Appeal.",
                "assertions": [{"text": "A statement.", "citations": citations}],
            }
        )

    async def complete(self, **_: Any) -> AgentResult[Draft]:
        call = LlmCallRecord(
            provider="mock",
            model="mock",
            input_tokens=1,
            output_tokens=1,
            latency_ms=1.0,
            cached=False,
            attempts=1,
        )
        return AgentResult(output=self._draft, llm_call=call)


async def quotes_after_repair(*citations: dict[str, Any]) -> list[tuple[str, str]]:
    writer = WriterAgentService(
        FixedDraft(list(citations)),  # type: ignore[arg-type]
        CaseRenderer(),
        QuoteMatcher(),
    )
    result = await writer.draft(CASE, [], CLAUSES, [], TRIAGE, previous=None, feedback=None)
    return [(c.source_id, c.quote) for c in result.output.assertions[0].citations]


async def test_a_quote_joining_two_sentences_of_the_note_becomes_two_citations() -> None:
    joined = "Established patient seen for right knee pain. Authorization obtained by phone"

    quotes = await quotes_after_repair({"kind": "DOCUMENT", "source_id": "NOTE", "quote": joined})

    assert quotes == [
        ("NOTE", "Established patient seen for right knee pain."),
        ("NOTE", "Authorization obtained by phone"),
    ]


async def test_a_clause_quote_shortened_with_an_ellipsis_is_split_at_the_ellipsis() -> None:
    shortened = "A claim denied for absent authorization ... issued before the date of service."

    quotes = await quotes_after_repair(
        {"kind": "CLAUSE", "source_id": "ACME-PA-4.2", "quote": shortened}
    )

    assert quotes == [
        ("ACME-PA-4.2", "A claim denied for absent authorization"),
        ("ACME-PA-4.2", "issued before the date of service."),
    ]


async def test_a_quote_with_any_invented_words_is_left_for_the_verifier() -> None:
    invented = (
        "Established patient seen for right knee pain. The injection was medically necessary."
    )

    quotes = await quotes_after_repair({"kind": "DOCUMENT", "source_id": "NOTE", "quote": invented})

    assert quotes == [("NOTE", invented)]


async def test_a_quote_found_whole_is_kept_whole() -> None:
    whole = "Authorization obtained by phone on 2026-05-29."

    quotes = await quotes_after_repair({"kind": "DOCUMENT", "source_id": "NOTE", "quote": whole})

    assert quotes == [("NOTE", whole)]


async def test_line_numbers_are_removed_before_the_quote_is_checked() -> None:
    quotes = await quotes_after_repair(
        {"kind": "DOCUMENT", "source_id": "NOTE", "quote": "4| Authorization obtained by phone"}
    )

    assert quotes == [("NOTE", "Authorization obtained by phone")]


async def test_fragments_too_short_to_prove_anything_are_not_kept_alone() -> None:
    # "Assessment:" is in the note, but a two-word piece is dropped, leaving one passage,
    # which is not enough to call the quote joined: it is left for the verifier.
    joined = "Assessment: primary osteoarthritis. Unrelated words never written"

    quotes = await quotes_after_repair({"kind": "DOCUMENT", "source_id": "NOTE", "quote": joined})

    assert quotes == [("NOTE", joined)]
