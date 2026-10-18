from collections import Counter
from pathlib import Path

from app.schemas.planted_draft import PlantedError
from tests.evals.generator.build import build_cases, stale_files
from tests.evals.generator.planted import (
    CLEAN_CONTROLS,
    PLANTED_PER_ERROR,
    build_planted,
    load_clauses,
    render_planted_files,
)
from tests.evals.planted_report import code_check_flags, load_planted

PLANTED_DIR = Path("tests/evals/planted")


def test_files_on_disk_are_what_the_generator_produces() -> None:
    planted = build_planted(build_cases(), seed=42)

    assert stale_files(render_planted_files(planted), PLANTED_DIR) == []


def test_there_are_the_planned_numbers_of_each_kind() -> None:
    counts = Counter(item.error for item in load_planted())

    assert counts[None] == CLEAN_CONTROLS
    assert {error: counts[error] for error in PlantedError} == dict.fromkeys(
        PlantedError, PLANTED_PER_ERROR
    )


def test_only_development_cases_are_used() -> None:
    assert all(item.case_id.startswith("DEV-") for item in load_planted())


def test_the_code_check_flags_no_clean_control() -> None:
    clauses = load_clauses()

    for item in load_planted():
        if item.error is None:
            assert code_check_flags(item, clauses) == set(), item.planted_id


def test_the_code_check_catches_every_error_in_a_citation_and_nothing_else() -> None:
    clauses = load_clauses()

    for item in load_planted():
        if item.error is not None and item.catchable_by_code:
            assert code_check_flags(item, clauses) == {item.planted_assertion_index}, (
                item.planted_id
            )


def test_errors_with_a_real_quote_pass_the_code_check_and_need_the_judge() -> None:
    """Records the limit of the first stage: these are the judge's job."""
    clauses = load_clauses()

    for item in load_planted():
        if item.error is not None and not item.catchable_by_code:
            assert code_check_flags(item, clauses) == set(), item.planted_id
