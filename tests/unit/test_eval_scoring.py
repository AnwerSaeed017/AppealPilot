import pytest

from app.clients.llm.errors import LlmRateLimitError, LlmUnavailableError
from app.core.exceptions import ModelProviderError
from app.schemas.recommended_action import RecommendedAction as A
from tests.evals.eval_results import CaseResult, SystemResult
from tests.evals.report import correct, mcnemar_p, unsafe
from tests.evals.runner import quota_exhausted


def case(expected: A | None, acceptable: tuple[A, ...] = ()) -> CaseResult:
    return CaseResult(case_id="DEV-001", scenario="s", expected=expected, acceptable=acceptable)


def did(action: A | None = None, rejected: bool = False) -> SystemResult:
    return SystemResult(action=action, rejected=rejected)


def test_the_labelled_action_or_an_accepted_alternative_is_correct() -> None:
    labelled = case(A.ESCALATE_TO_HUMAN, acceptable=(A.NO_ACTION,))

    assert correct(labelled, did(A.ESCALATE_TO_HUMAN))
    assert correct(labelled, did(A.NO_ACTION))
    assert not correct(labelled, did(A.REQUEST_DOCUMENTATION))
    assert not correct(labelled, did(None))


def test_invalid_input_is_correct_only_when_rejected() -> None:
    assert correct(case(None), did(rejected=True))
    assert not correct(case(None), did(A.NO_ACTION))


def test_only_an_unsupported_correction_or_appeal_is_unsafe() -> None:
    declined = case(A.NO_ACTION)

    assert unsafe(declined, did(A.APPEAL_WITH_EVIDENCE))
    assert unsafe(declined, did(A.CORRECT_AND_RESUBMIT))
    assert not unsafe(declined, did(A.ESCALATE_TO_HUMAN))
    assert not unsafe(case(A.APPEAL_WITH_EVIDENCE), did(A.APPEAL_WITH_EVIDENCE))


@pytest.mark.parametrize(
    ("graph_only", "baseline_only", "expected"),
    [(0, 0, 1.0), (5, 5, 1.0), (6, 0, 0.03125), (10, 2, 0.0386)],
)
def test_mcnemar_exact_p_value(graph_only: int, baseline_only: int, expected: float) -> None:
    assert mcnemar_p(graph_only, baseline_only) == pytest.approx(expected, abs=1e-4)


def test_a_rate_limit_anywhere_in_the_cause_chain_stops_the_run() -> None:
    error = ModelProviderError("failed")
    error.__cause__ = LlmRateLimitError("429 daily quota")

    assert quota_exhausted(error)


def test_other_provider_failures_do_not_stop_the_run() -> None:
    error = ModelProviderError("failed")
    error.__cause__ = LlmUnavailableError("503")

    assert not quota_exhausted(error)
