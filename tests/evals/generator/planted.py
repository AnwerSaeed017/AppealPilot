"""Drafts with one planted error each, plus clean controls, for testing the verifier.

Every draft is built from a development case's own label: one assertion per labelled
clause and one per labelled evidence line, each quoting its source exactly. That clean
draft is either kept as a control or given exactly one error.
"""

import json
import random
import re
from collections.abc import Callable
from pathlib import Path

from app.schemas.draft import Assertion, Citation, CitationKind, Draft
from app.schemas.eval_case import EvalCase, EvalSplit
from app.schemas.planted_draft import PlantedDraft, PlantedError
from app.schemas.policy_clause import PolicyClause
from app.schemas.policy_document import PolicyDocument

POLICIES_DIR = Path("seeders/policies")
PLANTED_PER_ERROR = 6
CLEAN_CONTROLS = 14

_NUMBER = re.compile(r"\b\d+\b")
_HEDGE = re.compile(r"\b(possible|suspected)\b", re.IGNORECASE)
_CLAUSE_PREFIX = "The policy states: "
_RECORD_PREFIX = "The record states: "


def load_clauses() -> dict[str, PolicyClause]:
    clauses: dict[str, PolicyClause] = {}
    for path in sorted(POLICIES_DIR.glob("*/*.json")):
        document = PolicyDocument.model_validate_json(path.read_text(encoding="utf-8"))
        clauses.update({clause.clause_id: clause for clause in document.to_clauses()})
    return clauses


def first_sentence(text: str) -> str:
    return text[: text.index(". ") + 1] if ". " in text else text


def clean_draft(case: EvalCase, clauses: dict[str, PolicyClause]) -> Draft:
    """A draft in which every assertion restates exactly what it quotes."""
    case_input = case.case_input()
    assertions: list[Assertion] = []
    for clause_id in case.expected.relevant_clause_ids:
        quote = first_sentence(clauses[clause_id].text)
        assertions.append(_assertion(_CLAUSE_PREFIX + quote, CitationKind.CLAUSE, clause_id, quote))
    for reference in case.expected.supporting_evidence:
        text = case_input.document_text(reference.document_id)
        assert text is not None
        line = text.splitlines()[reference.line_number - 1]
        assertions.append(
            _assertion(_RECORD_PREFIX + line, CitationKind.DOCUMENT, reference.document_id, line)
        )
    assert case.expected.action is not None
    return Draft(
        action=case.expected.action,
        summary=f"Draft for {case.case_id}.",
        assertions=tuple(assertions),
        correction=case.expected.expected_correction,
        missing_evidence=case.expected.missing_evidence,
    )


def _assertion(text: str, kind: CitationKind, source_id: str, quote: str) -> Assertion:
    return Assertion(text=text, citations=(Citation(kind=kind, source_id=source_id, quote=quote),))


def _replace(draft: Draft, index: int, assertion: Assertion) -> Draft:
    assertions = list(draft.assertions)
    assertions[index] = assertion
    return draft.model_copy(update={"assertions": tuple(assertions)})


def _bump_number(text: str) -> str:
    return _NUMBER.sub(lambda match: str(int(match.group()) + 30), text, count=1)


# Each planter returns the changed draft and the index of the planted assertion, or None
# when the error cannot be planted in this case.
Planted = tuple[Draft, int] | None


def _invented_clause(case: EvalCase, draft: Draft, clauses: dict[str, PolicyClause]) -> Planted:
    citation = draft.assertions[0].citations[0]
    invented = citation.source_id.rsplit("-", 1)[0] + "-99.9"
    changed = citation.model_copy(update={"source_id": invented})
    return _replace(draft, 0, draft.assertions[0].model_copy(update={"citations": (changed,)})), 0


def _clause_not_selected(case: EvalCase, draft: Draft, clauses: dict[str, PolicyClause]) -> Planted:
    payer_id = case.input["claim"]["payer_id"]
    other = next(
        clause
        for clause in clauses.values()
        if clause.payer_id == payer_id and clause.clause_id not in case.expected.relevant_clause_ids
    )
    quote = first_sentence(other.text)
    planted = _assertion(_CLAUSE_PREFIX + quote, CitationKind.CLAUSE, other.clause_id, quote)
    return _replace(draft, 0, planted), 0


def _fabricated_quote(case: EvalCase, draft: Draft, clauses: dict[str, PolicyClause]) -> Planted:
    quote = "The plan will pay such claims in full when the provider asks."
    source_id = draft.assertions[0].citations[0].source_id
    planted = _assertion(_CLAUSE_PREFIX + quote, CitationKind.CLAUSE, source_id, quote)
    return _replace(draft, 0, planted), 0


def _with_number(draft: Draft) -> int | None:
    return next(
        (
            index
            for index, assertion in enumerate(draft.assertions)
            if _NUMBER.search(assertion.citations[0].quote)
        ),
        None,
    )


def _number_changed_in_quote(
    case: EvalCase, draft: Draft, clauses: dict[str, PolicyClause]
) -> Planted:
    index = _with_number(draft)
    if index is None:
        return None
    assertion = draft.assertions[index]
    citation = assertion.citations[0]
    changed = citation.model_copy(update={"quote": _bump_number(citation.quote)})
    planted = Assertion(text=_bump_number(assertion.text), citations=(changed,))
    return _replace(draft, index, planted), index


def _number_changed_in_assertion(
    case: EvalCase, draft: Draft, clauses: dict[str, PolicyClause]
) -> Planted:
    index = _with_number(draft)
    if index is None:
        return None
    assertion = draft.assertions[index]
    planted = assertion.model_copy(update={"text": _bump_number(assertion.text)})
    return _replace(draft, index, planted), index


def _hedge_removed(case: EvalCase, draft: Draft, clauses: dict[str, PolicyClause]) -> Planted:
    line = next(
        (line for line in case.case_input().visit_note.text.splitlines() if _HEDGE.search(line)),
        None,
    )
    if line is None:
        return None
    definite = " ".join(_HEDGE.sub("confirmed", line).split())
    planted = _assertion(_RECORD_PREFIX + definite, CitationKind.DOCUMENT, "NOTE", line)
    return draft.model_copy(update={"assertions": (*draft.assertions, planted)}), len(
        draft.assertions
    )


def _conclusion_added(case: EvalCase, draft: Draft, clauses: dict[str, PolicyClause]) -> Planted:
    planted = draft.assertions[0].model_copy(
        update={"text": "Under this clause the payer is required to pay this claim in full."}
    )
    return _replace(draft, 0, planted), 0


_PLANTERS: dict[PlantedError, Callable[[EvalCase, Draft, dict[str, PolicyClause]], Planted]] = {
    PlantedError.INVENTED_CLAUSE: _invented_clause,
    PlantedError.CLAUSE_NOT_SELECTED: _clause_not_selected,
    PlantedError.FABRICATED_QUOTE: _fabricated_quote,
    PlantedError.NUMBER_CHANGED_IN_QUOTE: _number_changed_in_quote,
    PlantedError.NUMBER_CHANGED_IN_ASSERTION: _number_changed_in_assertion,
    PlantedError.HEDGE_REMOVED: _hedge_removed,
    PlantedError.CONCLUSION_ADDED: _conclusion_added,
}


def build_planted(cases: list[EvalCase], seed: int) -> list[PlantedDraft]:
    """The planted drafts and clean controls, from the development cases only."""
    clauses = load_clauses()
    usable = [
        case for case in cases if case.split is EvalSplit.DEV and case.expected.action is not None
    ]
    rng = random.Random(f"{seed}:planted")
    rng.shuffle(usable)

    built: list[tuple[EvalCase, Draft, PlantedError | None, int | None]] = [
        (case, clean_draft(case, clauses), None, None) for case in usable[:CLEAN_CONTROLS]
    ]
    for offset, (error, planter) in enumerate(_PLANTERS.items()):
        # Start each error type at a different case, so the types do not share cases.
        rotated = usable[offset * PLANTED_PER_ERROR :] + usable[: offset * PLANTED_PER_ERROR]
        planted_count = 0
        for case in rotated:
            result = planter(case, clean_draft(case, clauses), clauses)
            if result is None:
                continue
            built.append((case, result[0], error, result[1]))
            planted_count += 1
            if planted_count == PLANTED_PER_ERROR:
                break

    rng.shuffle(built)
    return [
        PlantedDraft(
            planted_id=f"PLANT-{number:03d}",
            case_id=case.case_id,
            selected_clause_ids=case.expected.relevant_clause_ids,
            draft=draft,
            error=error,
            planted_assertion_index=index,
        )
        for number, (case, draft, error, index) in enumerate(built, start=1)
    ]


def render_planted_files(planted: list[PlantedDraft]) -> dict[str, str]:
    """File contents keyed by file name."""
    return {
        f"{item.planted_id}.json": json.dumps(
            item.model_dump(mode="json"), indent=2, ensure_ascii=False
        )
        + "\n"
        for item in planted
    }


def write_planted_files(files: dict[str, str], planted_dir: Path) -> None:
    planted_dir.mkdir(parents=True, exist_ok=True)
    for stale in planted_dir.glob("PLANT-*.json"):
        stale.unlink()
    for name, content in files.items():
        (planted_dir / name).write_text(content, encoding="utf-8", newline="\n")
