"""Measure how often the labelled clauses are found for the development cases.

    python -m tests.evals.retrieval_report

Only the development cases are read. The locked cases are for release runs.
"""

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path

from dependency_injector import providers

from app.containers.container import Container
from app.core.settings import Settings
from app.schemas.eval_case import EvalCase

DEV_CASES_DIR = Path("tests/evals/cases/dev")
CUT_OFFS = (3, 5)


@dataclass(frozen=True)
class Recall:
    """Results for one configuration, at one cut-off."""

    cases: int
    any_found: int
    all_found: int
    clauses: int
    clauses_found: int


def load_dev_cases() -> list[EvalCase]:
    cases = [
        EvalCase.model_validate(json.loads(path.read_text(encoding="utf-8")))
        for path in sorted(DEV_CASES_DIR.glob("*.json"))
    ]
    return [case for case in cases if case.expected.action is not None]


async def selected_clause_ids(
    case: EvalCase, include_visit_note: bool, neighbour_sources: int
) -> list[str]:
    """The clause IDs the application selects for a case, in rank order."""
    container = Container()
    container.settings.override(
        providers.Object(
            Settings(
                _env_file=None,
                retrieval_limit=max(CUT_OFFS),
                retrieval_include_visit_note=include_visit_note,
                retrieval_neighbour_sources=neighbour_sources,
            )
        )
    )
    case_input = case.case_input()
    findings = await container.services.rules_engine_service().evaluate(case_input, case.as_of_date)
    selected = await container.services.case_retrieval_service().retrieve(case_input, findings)
    return [item.clause.clause_id for item in selected]


async def measure(include_visit_note: bool, neighbour_sources: int) -> dict[int, Recall]:
    """Recall at each cut-off for the application's own clause selection."""
    totals = {cut_off: [0, 0, 0, 0] for cut_off in CUT_OFFS}
    cases = load_dev_cases()
    for case in cases:
        ordered = await selected_clause_ids(case, include_visit_note, neighbour_sources)
        expected = set(case.expected.relevant_clause_ids)
        for cut_off in CUT_OFFS:
            hits = expected & set(ordered[:cut_off])
            totals[cut_off][0] += bool(hits)
            totals[cut_off][1] += hits == expected
            totals[cut_off][2] += len(expected)
            totals[cut_off][3] += len(hits)

    return {
        cut_off: Recall(len(cases), any_found, all_found, clauses, clauses_found)
        for cut_off, (any_found, all_found, clauses, clauses_found) in totals.items()
    }


async def main() -> None:
    print("| Visit note in search | Neighbours | Top | Any labelled clause | All | Clauses |")
    print("|---|---|---|---|---|---|")
    for include_visit_note in (False, True):
        for neighbour_sources in (0, 1, 2):
            results = await measure(include_visit_note, neighbour_sources)
            for cut_off, recall in results.items():
                print(
                    f"| {'yes' if include_visit_note else 'no'} | {neighbour_sources} | {cut_off} "
                    f"| {recall.any_found} of {recall.cases} "
                    f"| {recall.all_found} of {recall.cases} "
                    f"| {recall.clauses_found} of {recall.clauses} |"
                )


if __name__ == "__main__":
    asyncio.run(main())
