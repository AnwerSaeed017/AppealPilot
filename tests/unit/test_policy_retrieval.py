from pathlib import Path

import pytest
from dependency_injector import providers

from app.containers.container import Container
from app.core.settings import Settings
from app.interfaces.service.policy_retrieval_service import IPolicyRetrievalService
from app.schemas.case_input import CaseInput
from app.schemas.finding import Finding, FindingCode
from app.services.case_query_service import CaseQueryService
from app.utilities.bm25_scorer import Bm25Scorer
from app.utilities.word_tokenizer import WordTokenizer
from tests.evals.retrieval_report import measure
from tests.samples import case_input_payload


@pytest.fixture(scope="module")
def retrieval() -> IPolicyRetrievalService:
    container = Container()
    container.settings.override(
        providers.Object(Settings(_env_file=None, policies_dir=Path("seeders/policies")))
    )
    service: IPolicyRetrievalService = container.services.policy_retrieval_service()
    return service


def test_tokenizer_keeps_codes_and_drops_noise() -> None:
    tokens = WordTokenizer().tokenize("The claims for J7325 and 73721 must have Modifiers.")

    assert tokens == ("claim", "j7325", "73721", "modifier")


def test_tokenizer_leaves_short_words_and_double_s_alone() -> None:
    assert WordTokenizer().tokenize("gas loss access") == ("gas", "loss", "access")


def test_scorer_ranks_the_document_with_the_rare_term_first() -> None:
    documents = [["knee", "pain"], ["knee", "mri"], ["back", "pain"]]

    scores = Bm25Scorer().score(documents, ["knee", "mri"])

    assert scores[1] > scores[0] > scores[2] == 0


def test_scorer_handles_unknown_terms_and_no_documents() -> None:
    assert Bm25Scorer().score([["knee"]], ["elbow"]) == [0.0]
    assert Bm25Scorer().score([], ["knee"]) == []


def test_scorer_counts_a_repeated_query_term_once() -> None:
    documents = [["knee", "pain"], ["back", "pain"]]

    assert Bm25Scorer().score(documents, ["knee", "knee"]) == Bm25Scorer().score(
        documents, ["knee"]
    )


async def test_a_procedure_code_finds_the_clauses_that_name_it(
    retrieval: IPolicyRetrievalService,
) -> None:
    found = await retrieval.retrieve("TESS", "procedure code 73721 authorization", limit=3)

    assert "TESS-PA-1.1" in [item.clause.clause_id for item in found]
    assert [item.rank for item in found] == [1, 2, 3]
    assert found[0].score >= found[1].score >= found[2].score


async def test_only_the_named_payer_is_searched(retrieval: IPolicyRetrievalService) -> None:
    for payer_id in ("TESS", "QUIL"):
        found = await retrieval.retrieve(payer_id, "filing limit days date of service", limit=10)

        assert found
        assert {item.clause.payer_id for item in found} == {payer_id}


async def test_unknown_payer_and_unmatched_query_return_nothing(
    retrieval: IPolicyRetrievalService,
) -> None:
    assert await retrieval.retrieve("NOPE", "filing limit", limit=5) == ()
    assert await retrieval.retrieve("TESS", "zzzz qqqq", limit=5) == ()


def test_query_describes_the_denial_and_the_denied_lines_only() -> None:
    case_input = CaseInput.model_validate(case_input_payload())
    finding = Finding(code=FindingCode.NOTE_DATE_MISMATCH, message="A rule finding.")

    query = CaseQueryService(include_visit_note=False).build(case_input, [finding])

    assert "prior authorization absent" in query
    assert "procedure code 20610" in query  # line 2, the denied one
    assert "modifier" not in query  # the denial is not about modifiers
    assert "99214" not in query  # line 1 was not denied
    assert "A rule finding." in query
    assert "Established patient" not in query


def test_query_includes_the_note_only_when_asked() -> None:
    case_input = CaseInput.model_validate(case_input_payload())

    assert "Established patient" in CaseQueryService(include_visit_note=True).build(case_input, [])


async def test_recall_on_the_development_cases_does_not_fall() -> None:
    """A floor set from the first measurement, so a change that hurts search is noticed."""
    results = await measure(include_visit_note=False, neighbour_sources=1)

    assert results[3].any_found >= 50
    assert results[3].clauses_found >= 70
    assert results[5].any_found >= 52
    assert results[5].clauses_found >= 79
