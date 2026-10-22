"""Published evaluation results: how the workflow compares with a single-prompt baseline
on labelled cases, and how the deterministic stages perform on their own benchmarks.

Every count is a count out of a total, never a percentage: with this few cases per
bucket, a percentage suggests more precision than there is.
"""

from datetime import datetime

from pydantic import Field

from app.schemas.base_schema import BaseSchema


class Tally(BaseSchema):
    """A count out of a total, such as 44 of 54."""

    value: int = Field(ge=0)
    total: int = Field(ge=0)


class TallyPair(BaseSchema):
    workflow: Tally
    baseline: Tally


class NumberPair(BaseSchema):
    workflow: float = Field(ge=0)
    baseline: float = Field(ge=0)


class PairedComparison(BaseSchema):
    """The cases where exactly one system was right, and an exact McNemar test on them."""

    cases: int = Field(ge=0)
    workflow_only: int = Field(ge=0)
    baseline_only: int = Field(ge=0)
    p_value: float = Field(ge=0, le=1)


class ActionResult(BaseSchema):
    """How often each system was right on the cases labelled with one action."""

    # A recommended action, or INVALID_INPUT for cases that must be rejected.
    expected: str = Field(min_length=1)
    workflow: Tally
    baseline: Tally


class CaseOutcome(BaseSchema):
    """A case at least one system got wrong."""

    case_id: str = Field(min_length=1)
    scenario: str = Field(min_length=1)
    expected: str = Field(min_length=1)
    workflow: str = Field(min_length=1)
    workflow_correct: bool
    baseline: str = Field(min_length=1)
    baseline_correct: bool


class EvaluationRun(BaseSchema):
    """One run of both systems over the same labelled cases."""

    run_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    started_at: datetime
    split: str = Field(min_length=1)
    agent_model: str = Field(min_length=1)
    judge_model: str = Field(min_length=1)
    prompt_versions: dict[str, str]
    # Cases with a labelled action, and cases built to be rejected as invalid input.
    labelled_cases: int = Field(ge=0)
    invalid_cases: int = Field(ge=0)

    correct: TallyPair
    exact: TallyPair
    unsafe: TallyPair
    escalations: TallyPair
    declined_when_nothing_to_do: TallyPair
    injections: TallyPair
    invalid_rejected: TallyPair
    errors: TallyPair
    citations_in_source: TallyPair
    verified_drafts: Tally
    median_tokens: NumberPair
    median_model_calls: NumberPair
    median_model_ms: NumberPair

    paired: PairedComparison
    by_action: tuple[ActionResult, ...]
    misses: tuple[CaseOutcome, ...]


class PlantedErrorResult(BaseSchema):
    """How many drafts with one kind of planted error the code check caught."""

    error: str = Field(min_length=1)
    # "code" when the code check should catch it, "judge" when only the model judge can.
    stage: str = Field(min_length=1)
    caught: Tally


class VerifierBenchmark(BaseSchema):
    """The first, deterministic verification stage, measured on drafts with planted errors."""

    errors: tuple[PlantedErrorResult, ...]
    clean_drafts_flagged: Tally


class RetrievalBenchmark(BaseSchema):
    """How often the application's clause selection finds the labelled clauses."""

    cut_off: int = Field(ge=1)
    any_labelled_clause: Tally
    all_labelled_clauses: Tally
    labelled_clauses_found: Tally


class EvaluationBenchmarks(BaseSchema):
    """Everything the evaluation page shows."""

    published_at: datetime
    # The current run only: reviewers see the latest system against the baseline, never
    # a mix of runs made with different prompts.
    run: EvaluationRun
    verifier: VerifierBenchmark
    retrieval: RetrievalBenchmark
