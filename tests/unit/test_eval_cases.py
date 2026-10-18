import json
import random
from collections import Counter
from pathlib import Path

import pytest
from pydantic import TypeAdapter

from app.schemas.code_types import Npi
from app.schemas.eval_case import EvalCase, EvalSplit
from app.schemas.recommended_action import RecommendedAction
from tests.evals.generator.build import build_cases, render_files, stale_files
from tests.evals.generator.kit import make_npi
from tests.evals.generator.registry import ENTRIES
from tests.unit.test_policy_files import all_clauses

CASES_DIR = Path("tests/evals/cases")
CASE_FILES = sorted(CASES_DIR.glob("*/*.json"))

A = RecommendedAction
# The plan's table, less the cases written by hand: the injection attempts, and the
# hardest appeals.
PLANNED: dict[EvalSplit, dict[RecommendedAction | None, int]] = {
    EvalSplit.DEV: {
        A.CORRECT_AND_RESUBMIT: 11,
        A.APPEAL_WITH_EVIDENCE: 10,
        A.REQUEST_DOCUMENTATION: 9,
        A.NO_ACTION: 9,
        A.ESCALATE_TO_HUMAN: 7,
        None: 6,
    },
    EvalSplit.LOCKED: {
        A.CORRECT_AND_RESUBMIT: 6,
        A.APPEAL_WITH_EVIDENCE: 6,
        A.REQUEST_DOCUMENTATION: 5,
        A.NO_ACTION: 4,
        A.ESCALATE_TO_HUMAN: 4,
        None: 2,
    },
}


@pytest.fixture(scope="module")
def cases() -> list[EvalCase]:
    return build_cases()


def test_files_on_disk_are_what_the_generator_produces(cases: list[EvalCase]) -> None:
    assert stale_files(render_files(cases), CASES_DIR) == []


def test_generation_is_repeatable_and_depends_on_the_seed(cases: list[EvalCase]) -> None:
    assert render_files(build_cases()) == render_files(cases)
    assert render_files(build_cases(seed=7)) != render_files(cases)


def test_registry_keys_and_case_ids_are_unique(cases: list[EvalCase]) -> None:
    keys = [entry.key for entry in ENTRIES]

    assert len(set(keys)) == len(keys)
    assert len({case.case_id for case in cases}) == len(cases)


@pytest.mark.parametrize("split", list(EvalSplit))
def test_counts_per_action_match_the_plan(cases: list[EvalCase], split: EvalSplit) -> None:
    counts = Counter(case.expected.action for case in cases if case.split is split)

    assert dict(counts) == PLANNED[split]


@pytest.mark.parametrize("path", CASE_FILES, ids=lambda path: path.stem)
def test_case_file_is_valid_and_in_the_right_folder(path: Path) -> None:
    case = EvalCase.model_validate(json.loads(path.read_text(encoding="utf-8")))

    assert path.stem == case.case_id
    assert path.parent.name == case.split.value


def test_cited_clauses_exist_and_belong_to_the_case_payer(cases: list[EvalCase]) -> None:
    clauses = all_clauses()

    for case in cases:
        payer_id = case.input["claim"]["payer_id"]
        for clause_id in case.expected.relevant_clause_ids:
            assert clause_id in clauses, f"{case.case_id} cites missing clause {clause_id}"
            assert clauses[clause_id].payer_id == payer_id, case.case_id


def test_every_valid_case_names_at_least_one_clause(cases: list[EvalCase]) -> None:
    for case in cases:
        if case.expected.action is not None:
            assert case.expected.relevant_clause_ids, case.case_id


def test_evidence_lines_are_not_blank(cases: list[EvalCase]) -> None:
    for case in cases:
        if case.expected.action is None:
            continue
        case_input = case.case_input()
        for reference in case.expected.supporting_evidence:
            text = case_input.document_text(reference.document_id)
            assert text is not None
            assert text.splitlines()[reference.line_number - 1].strip(), case.case_id


def test_dates_run_in_order(cases: list[EvalCase]) -> None:
    for case in cases:
        if case.expected.action is None:
            continue
        case_input = case.case_input()
        service = max(line.service_date for line in case_input.claim.lines)
        assert service <= case_input.claim.submitted_date <= case_input.denial.denial_date
        assert case_input.denial.denial_date <= case.as_of_date
        for prior in case_input.prior_claims:
            assert service <= prior.received_date < case_input.claim.submitted_date
        for document in case_input.supporting_documents:
            assert document.document_date <= case.as_of_date, case.case_id


def test_no_scenario_appears_in_both_splits_with_the_same_payer() -> None:
    seen: dict[tuple[str, str, str], EvalSplit] = {}
    for entry in ENTRIES:
        signature = (
            entry.scenario.__name__,
            entry.payer,
            json.dumps(entry.params, sort_keys=True),
        )
        assert seen.setdefault(signature, entry.split) is entry.split, entry.key


def test_make_npi_always_produces_a_valid_npi() -> None:
    adapter = TypeAdapter(Npi)
    rng = random.Random(1)

    for _ in range(200):
        adapter.validate_python(make_npi(rng))
