from app.agents.states.case_state import CaseState
from app.constants.agents import (
    MAX_MODEL_CALLS_PER_CASE,
    MAX_WRITER_REVISIONS,
    STEP_REVIEW,
    STEP_WRITER,
)


def route_after_verification(state: CaseState) -> str:
    """Back to the writer while rewrites and model calls remain, otherwise on to review."""
    failed = state.verification is not None and not state.verification.passed
    rewrites_used = state.writer_attempts - 1
    model_calls = sum(event.llm_call.attempts for event in state.audit if event.llm_call)
    if failed and rewrites_used < MAX_WRITER_REVISIONS and model_calls < MAX_MODEL_CALLS_PER_CASE:
        return STEP_WRITER
    return STEP_REVIEW
