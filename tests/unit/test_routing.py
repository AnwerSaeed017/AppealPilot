from datetime import UTC, date, datetime

from app.agents.routing.after_verification import route_after_verification
from app.agents.states.case_state import CaseState
from app.constants.agents import MAX_MODEL_CALLS_PER_CASE
from app.schemas.audit_event import AuditEvent, LlmCallRecord
from app.schemas.case_input import CaseInput
from app.schemas.verification_report import AssertionVerdict, VerificationReport
from tests.samples import case_input_payload

PASSED = VerificationReport(verdicts=(AssertionVerdict(assertion_index=0, supported=True),))
FAILED = VerificationReport(
    verdicts=(AssertionVerdict(assertion_index=0, supported=False, problems=("bad quote",)),)
)


def model_event(attempts: int) -> AuditEvent:
    return AuditEvent(
        step="writer",
        at=datetime(2026, 10, 12, tzinfo=UTC),
        summary="A model step.",
        llm_call=LlmCallRecord(
            provider="mock",
            model="mock",
            input_tokens=0,
            output_tokens=0,
            latency_ms=0,
            cached=False,
            attempts=attempts,
        ),
    )


def state(report: VerificationReport, drafts: int, model_calls: int = 4) -> CaseState:
    return CaseState(
        case_id="CASE-1",
        as_of=date(2026, 7, 1),
        case_input=CaseInput.model_validate(case_input_payload()),
        verification=report,
        writer_attempts=drafts,
        audit=(model_event(model_calls),),
    )


def test_a_passed_draft_goes_to_review() -> None:
    assert route_after_verification(state(PASSED, drafts=1)) == "review"


def test_a_failed_draft_goes_back_to_the_writer_twice_and_no_more() -> None:
    assert route_after_verification(state(FAILED, drafts=1)) == "writer"
    assert route_after_verification(state(FAILED, drafts=2)) == "writer"
    assert route_after_verification(state(FAILED, drafts=3)) == "review"


def test_a_failed_draft_goes_to_review_once_the_case_has_used_its_model_calls() -> None:
    under = state(FAILED, drafts=1, model_calls=MAX_MODEL_CALLS_PER_CASE - 1)
    at_limit = state(FAILED, drafts=1, model_calls=MAX_MODEL_CALLS_PER_CASE)

    assert route_after_verification(under) == "writer"
    assert route_after_verification(at_limit) == "review"
