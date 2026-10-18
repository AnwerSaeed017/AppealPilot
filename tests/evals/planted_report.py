"""How many planted errors the code check catches, and how many clean drafts it flags.

    python -m tests.evals.planted_report

This measures the first verification stage only. The second stage is a model judge and
needs a real model to measure.
"""

import json
from collections import Counter
from pathlib import Path

from app.schemas.case_clause import CaseClause, ClauseOrigin
from app.schemas.eval_case import EvalCase
from app.schemas.planted_draft import CODE_CATCHABLE, PlantedDraft, PlantedError
from app.schemas.policy_clause import PolicyClause
from app.services.citation_verifier_service import CitationVerifierService
from app.utilities.quote_matcher import QuoteMatcher
from tests.evals.generator.planted import load_clauses

PLANTED_DIR = Path("tests/evals/planted")
DEV_CASES_DIR = Path("tests/evals/cases/dev")


def load_planted() -> list[PlantedDraft]:
    return [
        PlantedDraft.model_validate(json.loads(path.read_text(encoding="utf-8")))
        for path in sorted(PLANTED_DIR.glob("PLANT-*.json"))
    ]


def code_check_flags(item: PlantedDraft, clauses: dict[str, PolicyClause]) -> set[int]:
    """The assertions of a planted draft that the code check marks as unsupported."""
    case_path = DEV_CASES_DIR / f"{item.case_id}.json"
    case = EvalCase.model_validate(json.loads(case_path.read_text(encoding="utf-8")))
    selected = [
        CaseClause(clause=clauses[clause_id], rank=rank, origin=ClauseOrigin.SEARCH)
        for rank, clause_id in enumerate(item.selected_clause_ids, start=1)
    ]
    report = CitationVerifierService(QuoteMatcher()).check(item.draft, case.case_input(), selected)
    return {verdict.assertion_index for verdict in report.failures()}


def main() -> None:
    clauses = load_clauses()
    caught: Counter[str] = Counter()
    total: Counter[str] = Counter()
    controls = false_alarms = stray_flags = 0

    for item in load_planted():
        flagged = code_check_flags(item, clauses)
        if item.error is None:
            controls += 1
            false_alarms += bool(flagged)
            continue
        total[item.error.value] += 1
        caught[item.error.value] += item.planted_assertion_index in flagged
        stray_flags += bool(flagged - {item.planted_assertion_index})

    print("| Planted error | Stage that should catch it | Caught by the code check |")
    print("|---|---|---|")
    for item_error, count in total.items():
        stage = "code" if PlantedError(item_error) in CODE_CATCHABLE else "judge"
        print(f"| {item_error} | {stage} | {caught[item_error]} of {count} |")
    print()
    print(f"Clean controls wrongly flagged: {false_alarms} of {controls}")
    print(f"Planted drafts with a second, unplanted assertion flagged: {stray_flags}")


if __name__ == "__main__":
    main()
