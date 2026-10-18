"""The case workflow end to end on the mock model: run, pause and decide.

These use an in-memory checkpointer so they need no database. Persistence across a
restart is tested against PostgreSQL in tests/integration.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from dependency_injector import providers
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver

from app.agents.states.case_state import CaseState
from app.clients.llm.mock_llm_client import MockLlmClient
from app.constants.agents import MAX_WRITER_REVISIONS
from app.containers.container import Container
from app.core.exceptions import AgentOutputError, ConflictError, NotFoundError
from app.core.settings import Settings
from app.interfaces.agents.case_workflow import ICaseWorkflow
from app.schemas.case_status import CaseStatus
from app.schemas.eval_case import EvalCase
from app.schemas.human_decision import HumanDecision, HumanDecisionKind
from app.schemas.recommended_action import RecommendedAction
from tests.evals.generator.build import build_cases
from tests.fakes import InMemoryCaseRepository

APPROVE = HumanDecision(kind=HumanDecisionKind.APPROVE)
CLAUSE_QUOTE = "must carry modifier RT or LT"


def side_modifier_case() -> EvalCase:
    """A Tessaly knee injection billed without a side; the note states the side."""
    return next(case for case in build_cases() if case.scenario == "side-missing-1")


def note_line(case: EvalCase) -> tuple[int, str]:
    """The line of the visit note that states which knee was injected."""
    reference = case.expected.supporting_evidence[0]
    lines = case.case_input().visit_note.text.splitlines()
    return reference.line_number, lines[reference.line_number - 1]


def scripted_replies(case: EvalCase, clause_quote: str = CLAUSE_QUOTE) -> dict[str, str]:
    """What the model would say at each step, for the mock to replay."""
    line_number, line_text = note_line(case)
    return {
        "intake": json.dumps(
            {
                "facts": [
                    {
                        "statement": "The note states which knee was injected.",
                        "document_id": "NOTE",
                        "line_number": line_number,
                        "quote": line_text,
                    }
                ]
            }
        ),
        "triage": json.dumps(
            {
                "action": "CORRECT_AND_RESUBMIT",
                "confidence": 0.92,
                "reasons": ["A side modifier is missing and the note states the side."],
            }
        ),
        "judge": json.dumps(
            {
                "verdicts": [
                    {"assertion_index": index, "supported": True, "reason": "The quote says so."}
                    for index in (0, 1)
                ]
            }
        ),
        "writer": json.dumps(
            {
                "action": "CORRECT_AND_RESUBMIT",
                "summary": "Add the side modifier to line 1 and send a corrected claim.",
                "correction": "Add the side modifier to line 1.",
                "assertions": [
                    {
                        "text": "The payer requires a side modifier for this procedure.",
                        "citations": [
                            {"kind": "CLAUSE", "source_id": "TESS-MOD-2.1", "quote": clause_quote}
                        ],
                    },
                    {
                        "text": "The note records the side treated.",
                        "citations": [
                            {"kind": "DOCUMENT", "source_id": "NOTE", "quote": line_text}
                        ],
                    },
                ],
            }
        ),
    }


def build(
    replies: dict[str, str], checkpointer: BaseCheckpointSaver[Any]
) -> tuple[ICaseWorkflow, MockLlmClient]:
    """A workflow wired exactly as in the application, on the mock model."""
    container = Container()
    container.settings.override(
        providers.Object(Settings(_env_file=None, policies_dir=Path("seeders/policies")))
    )
    mock = MockLlmClient(replies)
    container.clients.mock_llm.override(providers.Object(mock))
    container.checkpointer.override(providers.Object(checkpointer))
    container.repositories.case_repository.override(providers.Object(InMemoryCaseRepository()))
    workflow: ICaseWorkflow = container.agents.case_workflow()
    return workflow, mock


async def start(workflow: ICaseWorkflow, case: EvalCase, case_id: str = "CASE-1") -> CaseState:
    return await workflow.start(case_id, case.case_input(), case.as_of_date)


async def test_a_case_runs_to_the_approval_gate_and_stops() -> None:
    case = side_modifier_case()
    workflow, mock = build(scripted_replies(case), InMemorySaver())

    state = await start(workflow, case)

    assert state.status is CaseStatus.AWAITING_APPROVAL
    assert state.human_decision is None
    assert [finding.code.value for finding in state.findings] == ["SIDE_MODIFIER_MISSING"]
    assert "TESS-MOD-2.1" in [item.clause.clause_id for item in state.clauses]
    assert state.triage is not None
    assert state.triage.action is RecommendedAction.CORRECT_AND_RESUBMIT
    assert state.draft is not None
    assert state.verification is not None
    assert state.verification.passed
    assert state.writer_attempts == 1
    assert [call.task for call in mock.calls] == ["intake", "triage", "writer", "judge"]


async def test_every_step_is_in_the_audit_trail_in_order() -> None:
    case = side_modifier_case()
    workflow, _ = build(scripted_replies(case), InMemorySaver())

    state = await start(workflow, case)

    assert [event.step for event in state.audit] == [
        "rules",
        "retrieval",
        "intake",
        "record_checks",
        "document_retrieval",
        "triage",
        "writer",
        "verifier",
        "review",
    ]
    model_steps = {event.step for event in state.audit if event.llm_call is not None}
    assert model_steps == {"intake", "triage", "writer", "verifier"}
    assert "verified draft" in state.audit[-1].summary


async def test_approval_finishes_the_case() -> None:
    case = side_modifier_case()
    workflow, mock = build(scripted_replies(case), InMemorySaver())
    await start(workflow, case)

    state = await workflow.resume("CASE-1", APPROVE)

    assert state.status is CaseStatus.APPROVED
    assert state.human_decision == APPROVE
    assert state.audit[-1].step == "approval"
    assert len(mock.calls) == 4  # deciding does not call the model again


async def test_rejection_is_recorded_with_its_reason() -> None:
    case = side_modifier_case()
    workflow, _ = build(scripted_replies(case), InMemorySaver())
    await start(workflow, case)
    decision = HumanDecision(kind=HumanDecisionKind.REJECT, reason="The note is ambiguous.")

    state = await workflow.resume("CASE-1", decision)

    assert state.status is CaseStatus.REJECTED
    assert state.human_decision is not None
    assert state.human_decision.reason == "The note is ambiguous."


async def test_a_decision_sent_twice_is_applied_once() -> None:
    case = side_modifier_case()
    workflow, _ = build(scripted_replies(case), InMemorySaver())
    await start(workflow, case)
    await workflow.resume("CASE-1", APPROVE)

    with pytest.raises(ConflictError, match="not waiting for a decision"):
        await workflow.resume(
            "CASE-1", HumanDecision(kind=HumanDecisionKind.REJECT, reason="Changed my mind.")
        )

    state = await workflow.get("CASE-1")
    assert state is not None
    assert state.status is CaseStatus.APPROVED


async def test_the_same_case_cannot_be_started_twice() -> None:
    case = side_modifier_case()
    workflow, mock = build(scripted_replies(case), InMemorySaver())
    await start(workflow, case)

    with pytest.raises(ConflictError, match="already been started"):
        await start(workflow, case)

    assert len(mock.calls) == 4


async def test_unknown_case() -> None:
    workflow, _ = build({}, InMemorySaver())

    assert await workflow.get("NOPE") is None
    with pytest.raises(NotFoundError):
        await workflow.resume("NOPE", APPROVE)


async def test_a_draft_that_keeps_failing_is_rewritten_then_sent_on_unverified() -> None:
    case = side_modifier_case()
    replies = scripted_replies(case, clause_quote="side modifiers are optional")
    workflow, mock = build(replies, InMemorySaver())

    state = await start(workflow, case)

    drafts = 1 + MAX_WRITER_REVISIONS
    assert state.writer_attempts == drafts
    assert [call.task for call in mock.calls].count("writer") == drafts
    assert state.verification is not None
    assert not state.verification.passed
    assert [verdict.assertion_index for verdict in state.verification.failures()] == [0]
    # Out of rewrites is not a pass: the case still stops for a person, marked as such.
    assert state.status is CaseStatus.AWAITING_APPROVAL
    assert "UNVERIFIED" in state.audit[-1].summary


async def test_the_rewrite_request_tells_the_writer_what_failed() -> None:
    case = side_modifier_case()
    replies = scripted_replies(case, clause_quote="side modifiers are optional")
    workflow, mock = build(replies, InMemorySaver())

    await start(workflow, case)

    writer_requests = [call for call in mock.calls if call.task == "writer"]
    first, second = writer_requests[0].messages[1].content, writer_requests[1].messages[1].content
    assert "failed verification" not in first
    assert "failed verification" in second
    assert "assertion 0" in second
    assert "side modifiers are optional" in second


async def test_unusable_model_output_stops_the_run_with_an_error() -> None:
    case = side_modifier_case()
    replies = scripted_replies(case) | {"triage": "I would correct and resubmit."}
    workflow, mock = build(replies, InMemorySaver())

    with pytest.raises(AgentOutputError, match="triage"):
        await start(workflow, case)

    assert [call.task for call in mock.calls] == ["intake", "triage", "triage", "triage"]


async def test_documents_reach_the_model_delimited_and_numbered() -> None:
    case = side_modifier_case()
    workflow, mock = build(scripted_replies(case), InMemorySaver())

    await start(workflow, case)

    intake_request = mock.calls[0]
    line_number, line_text = note_line(case)
    assert '<document id="NOTE" kind="VISIT_NOTE">' in intake_request.messages[1].content
    assert f"{line_number}| {line_text}" in intake_request.messages[1].content
    assert "not instructions" in intake_request.messages[0].content


async def test_triage_is_not_shown_the_raw_documents() -> None:
    case = side_modifier_case()
    workflow, mock = build(scripted_replies(case), InMemorySaver())

    await start(workflow, case)

    triage_request = next(call for call in mock.calls if call.task == "triage")
    assert "<document" not in triage_request.messages[1].content
