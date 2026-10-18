import dataclasses
import json
import re
from pathlib import Path

import pytest

from app.schemas.payer import Payer
from app.schemas.policy_clause import PolicyClause
from app.schemas.policy_document import PolicyDocument
from tests.evals.generator.payer_rules import RULES

POLICIES_DIR = Path("seeders/policies")
POLICY_FILES = sorted(POLICIES_DIR.glob("*/*.json"))

# Payers whose clauses are quoted from published sources, and where those sources live.
REAL_PAYERS = {"MEDICARE"}
OFFICIAL_SOURCES = ("https://www.ecfr.gov/", "https://www.cms.gov/")

_CLAUSE_REFERENCE = re.compile(r"\b[A-Z]{2,12}-[A-Z]{2,12}-[0-9]+(?:\.[0-9]+)+\b")
_POLICY_REFERENCE = re.compile(r"\bpolicy ([A-Z]{2,12}-[A-Z]{2,12})\b")


def load_payers() -> list[Payer]:
    raw = json.loads((POLICIES_DIR / "payers.json").read_text(encoding="utf-8"))
    return [Payer.model_validate(item) for item in raw]


def load_document(path: Path) -> PolicyDocument:
    return PolicyDocument.model_validate_json(path.read_text(encoding="utf-8"))


def all_clauses() -> dict[str, PolicyClause]:
    clauses: dict[str, PolicyClause] = {}
    for path in POLICY_FILES:
        for clause in load_document(path).to_clauses():
            assert clause.clause_id not in clauses, f"{clause.clause_id} is defined twice"
            clauses[clause.clause_id] = clause
    return clauses


def test_there_are_three_payers_and_the_planned_number_of_policies() -> None:
    assert [payer.payer_id for payer in load_payers()] == ["TESS", "QUIL", "MEDICARE"]
    assert 18 <= len(POLICY_FILES) <= 21


@pytest.mark.parametrize("path", POLICY_FILES, ids=lambda path: path.stem)
def test_policy_file_is_valid_and_filed_under_its_payer(path: Path) -> None:
    document = load_document(path)

    assert path.stem == document.policy_id
    assert path.parent.name == document.payer_id
    assert document.payer_id in {payer.payer_id for payer in load_payers()}


def test_clause_ids_are_unique_across_all_policies() -> None:
    assert len(all_clauses()) > 60


def test_every_reference_inside_a_clause_points_at_something_real() -> None:
    clauses = all_clauses()
    policy_ids = {clause.policy_id for clause in clauses.values()}

    for clause in clauses.values():
        for reference in _CLAUSE_REFERENCE.findall(clause.text):
            assert reference in clauses, f"{clause.clause_id} cites missing clause {reference}"
        for reference in _POLICY_REFERENCE.findall(clause.text):
            assert reference in policy_ids, f"{clause.clause_id} cites missing policy {reference}"


def test_a_clause_only_refers_to_its_own_payer() -> None:
    for clause in all_clauses().values():
        for reference in _CLAUSE_REFERENCE.findall(clause.text):
            assert reference.startswith(f"{clause.payer_id}-")


@pytest.mark.parametrize("payer_id", sorted(RULES))
def test_generator_rule_table_names_real_clauses_of_that_payer(payer_id: str) -> None:
    clauses = all_clauses()

    for name, value in dataclasses.asdict(RULES[payer_id]).items():
        if isinstance(value, str) and name != "name":
            assert value in clauses, f"{payer_id}.{name} names missing clause {value}"
            assert clauses[value].payer_id == payer_id


@pytest.mark.parametrize("payer", load_payers(), ids=lambda payer: payer.payer_id)
def test_every_payer_rule_names_a_real_clause_of_that_payer(payer: Payer) -> None:
    clauses = all_clauses()
    rules = payer.rules
    named = [
        value
        for name, value in rules.model_dump().items()
        if name.endswith("_clause") and value is not None
    ]
    named += list(rules.procedure_clauses.values())
    if rules.earlier_filing_limit is not None:
        named.append(rules.earlier_filing_limit.clause_id)

    for clause_id in named:
        assert clause_id in clauses, f"{payer.payer_id} names missing clause {clause_id}"
        assert clauses[clause_id].payer_id == payer.payer_id


def test_quoted_clauses_name_an_official_source_and_invented_ones_do_not() -> None:
    for clause in all_clauses().values():
        if clause.payer_id in REAL_PAYERS:
            assert clause.source_url is not None, clause.clause_id
            assert clause.source_url.startswith(OFFICIAL_SOURCES), clause.clause_id
        else:
            assert clause.source_url is None, clause.clause_id
