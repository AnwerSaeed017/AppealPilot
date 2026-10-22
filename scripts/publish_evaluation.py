"""Publish an evaluation run's results for the API and the web app's evaluation page.

    uv run python -m scripts.publish_evaluation --run dev-full-v3 \
        --title "Development set, prompts v3" --summary "..."

Scores the run with the same rules as `tests.evals.report`, measures the deterministic
benchmarks (planted errors for the verifier's code stage, clause recall for retrieval)
on the current code, and writes everything to `seeders/evaluations/benchmarks.json`.
The file holds one run, the current one, which replaces whatever was published before:
reviewers see the latest system against the baseline, never a mix of runs.
"""

import argparse
import asyncio
import statistics
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path

from app.core.settings import Settings
from app.schemas.evaluation import (
    ActionResult,
    CaseOutcome,
    EvaluationBenchmarks,
    EvaluationRun,
    NumberPair,
    PairedComparison,
    PlantedErrorResult,
    RetrievalBenchmark,
    Tally,
    TallyPair,
    VerifierBenchmark,
)
from app.schemas.recommended_action import RecommendedAction
from tests.evals import planted_report, retrieval_report
from tests.evals.eval_results import CaseResult, RunInfo, System, SystemResult
from tests.evals.report import ACTS, correct, mcnemar_p, unsafe

RESULTS_DIR = Path("tests/evals/results")
INVALID_INPUT = "INVALID_INPUT"

Test = Callable[[CaseResult, SystemResult], bool]


def load_run(name: str) -> tuple[RunInfo, list[CaseResult]]:
    run_dir = RESULTS_DIR / name
    info = RunInfo.model_validate_json((run_dir / "run.json").read_text(encoding="utf-8"))
    cases = [
        CaseResult.model_validate_json(path.read_text(encoding="utf-8"))
        for path in sorted(run_dir.glob("*.json"))
        if path.name not in {"run.json", "summary.json"}
    ]
    return info, cases


def pairs(cases: Sequence[CaseResult], system: System) -> list[tuple[CaseResult, SystemResult]]:
    return [(case, case.results[system]) for case in cases if system in case.results]


def tally(items: Sequence[tuple[CaseResult, SystemResult]], test: Test) -> Tally:
    return Tally(value=sum(test(case, result) for case, result in items), total=len(items))


def tally_pair(cases: Sequence[CaseResult], test: Test) -> TallyPair:
    return TallyPair(
        workflow=tally(pairs(cases, System.GRAPH), test),
        baseline=tally(pairs(cases, System.BASELINE), test),
    )


def median_pair(cases: Sequence[CaseResult], value: Callable[[SystemResult], float]) -> NumberPair:
    def median(system: System) -> float:
        ran = [
            value(result)
            for case, result in pairs(cases, system)
            if case.expected is not None and result.error is None
        ]
        # Rounded as the text report rounds, so the page and REPORT.md agree.
        return float(round(statistics.median(ran))) if ran else 0.0

    return NumberPair(workflow=median(System.GRAPH), baseline=median(System.BASELINE))


def label(result: SystemResult | None) -> str:
    if result is None:
        return "not run"
    if result.error:
        return "error"
    if result.rejected:
        return "rejected"
    return result.action.value if result.action else "none"


def score_run(info: RunInfo, cases: list[CaseResult], title: str, summary: str) -> EvaluationRun:
    labelled = [case for case in cases if case.expected is not None]
    invalid = [case for case in cases if case.expected is None]
    ran = [case for case in labelled if all(not result.error for result in case.results.values())]

    def subset(test: Callable[[CaseResult], bool]) -> list[CaseResult]:
        return [case for case in labelled if test(case)]

    both = [case for case in labelled if all(system in case.results for system in System)]
    workflow_only = sum(
        correct(c, c.results[System.GRAPH]) and not correct(c, c.results[System.BASELINE])
        for c in both
    )
    baseline_only = sum(
        correct(c, c.results[System.BASELINE]) and not correct(c, c.results[System.GRAPH])
        for c in both
    )

    by_action = []
    for action in [*RecommendedAction, None]:
        group = [case for case in cases if case.expected is action]
        if group:
            pair = tally_pair(group, correct)
            by_action.append(
                ActionResult(
                    expected=action.value if action else INVALID_INPUT,
                    workflow=pair.workflow,
                    baseline=pair.baseline,
                )
            )

    misses = []
    for case in cases:
        graph, baseline = case.results.get(System.GRAPH), case.results.get(System.BASELINE)
        graph_ok = graph is not None and correct(case, graph)
        baseline_ok = baseline is not None and correct(case, baseline)
        if graph_ok and baseline_ok:
            continue
        misses.append(
            CaseOutcome(
                case_id=case.case_id,
                scenario=case.scenario,
                expected=case.expected.value if case.expected else INVALID_INPUT,
                workflow=label(graph),
                workflow_correct=graph_ok,
                baseline=label(baseline),
                baseline_correct=baseline_ok,
            )
        )

    def cited(system: System) -> Tally:
        results = [result for case, result in pairs(ran, system)]
        total = sum(result.citations for result in results)
        failed = sum(result.citations_failed for result in results)
        return Tally(value=total - failed, total=total)

    return EvaluationRun(
        run_id=info.run,
        title=title,
        summary=summary,
        started_at=info.started_at,
        split=info.split,
        agent_model=info.agent_model,
        judge_model=info.judge_model,
        prompt_versions=info.prompt_versions,
        labelled_cases=len(labelled),
        invalid_cases=len(invalid),
        correct=tally_pair(labelled, correct),
        exact=tally_pair(labelled, lambda case, result: result.action is case.expected),
        unsafe=tally_pair(labelled, unsafe),
        escalations=tally_pair(
            subset(lambda case: case.expected is RecommendedAction.ESCALATE_TO_HUMAN), correct
        ),
        declined_when_nothing_to_do=tally_pair(
            subset(lambda case: case.expected is RecommendedAction.NO_ACTION),
            lambda case, result: result.action not in ACTS,
        ),
        injections=tally_pair(subset(lambda case: "injection" in case.tags), correct),
        invalid_rejected=tally_pair(invalid, correct),
        errors=tally_pair(labelled, lambda case, result: result.error is not None),
        citations_in_source=TallyPair(
            workflow=cited(System.GRAPH), baseline=cited(System.BASELINE)
        ),
        verified_drafts=tally(
            [(case, result) for case, result in pairs(ran, System.GRAPH)],
            lambda case, result: bool(result.verified),
        ),
        median_tokens=median_pair(cases, lambda result: result.input_tokens + result.output_tokens),
        median_model_calls=median_pair(cases, lambda result: result.model_calls),
        median_model_ms=median_pair(cases, lambda result: result.latency_ms),
        paired=PairedComparison(
            cases=len(both),
            workflow_only=workflow_only,
            baseline_only=baseline_only,
            p_value=mcnemar_p(workflow_only, baseline_only),
        ),
        by_action=tuple(by_action),
        misses=tuple(misses),
    )


def verifier_benchmark() -> VerifierBenchmark:
    summary = planted_report.measure()
    return VerifierBenchmark(
        errors=tuple(
            PlantedErrorResult(
                error=error,
                stage=summary.stage(error),
                caught=Tally(value=summary.caught.get(error, 0), total=total),
            )
            for error, total in sorted(summary.total.items())
        ),
        clean_drafts_flagged=Tally(value=summary.false_alarms, total=summary.controls),
    )


async def retrieval_benchmark(settings: Settings) -> RetrievalBenchmark:
    """Recall with the application's own settings, at its own clause limit."""
    results = await retrieval_report.measure(
        settings.retrieval_include_visit_note, settings.retrieval_neighbour_sources
    )
    cut_off = settings.retrieval_limit
    recall = results[cut_off]
    return RetrievalBenchmark(
        cut_off=cut_off,
        any_labelled_clause=Tally(value=recall.any_found, total=recall.cases),
        all_labelled_clauses=Tally(value=recall.all_found, total=recall.cases),
        labelled_clauses_found=Tally(value=recall.clauses_found, total=recall.clauses),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish an evaluation run.")
    parser.add_argument("--run", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument(
        "--exclude",
        nargs="*",
        default=[],
        help="Case IDs to leave out, such as cases written to test a fix, so the published "
        "comparison stays on the same case set as before.",
    )
    arguments = parser.parse_args()

    settings = Settings()
    target = settings.evaluations_file
    info, cases = load_run(arguments.run)
    excluded = set(arguments.exclude)
    cases = [case for case in cases if case.case_id not in excluded]
    benchmarks = EvaluationBenchmarks(
        published_at=datetime.now(UTC),
        run=score_run(info, cases, arguments.title, arguments.summary),
        verifier=verifier_benchmark(),
        retrieval=asyncio.run(retrieval_benchmark(settings)),
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(benchmarks.model_dump_json(indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {target}: run {benchmarks.run.run_id}")


if __name__ == "__main__":
    main()
