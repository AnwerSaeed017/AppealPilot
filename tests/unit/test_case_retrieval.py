from collections.abc import Sequence

from app.interfaces.repository.policy_repository import IPolicyRepository
from app.interfaces.service.case_query_service import ICaseQueryService
from app.interfaces.service.policy_retrieval_service import IPolicyRetrievalService
from app.schemas.case_clause import ClauseOrigin
from app.schemas.case_input import CaseInput
from app.schemas.finding import Finding, FindingCode
from app.schemas.note_fact import NoteFact
from app.schemas.payer import Payer
from app.schemas.policy_clause import PolicyClause
from app.schemas.retrieved_clause import RetrievedClause
from app.services.case_retrieval_service import CaseRetrievalService
from tests.samples import case_input_payload


def clause(clause_id: str) -> PolicyClause:
    payer_id, policy = clause_id.split("-")[:2]
    return PolicyClause(
        clause_id=clause_id,
        policy_id=f"{payer_id}-{policy}",
        payer_id=payer_id,
        policy_title="A policy",
        section_heading="A section",
        text="Some text.",
        effective_from="2026-01-01",
    )


# The sample case's payer is ACME. Its policy has two sections of two clauses each.
ACME = [clause(f"ACME-PA-{number}") for number in ("1.1", "1.2", "2.1", "2.2")]
OTHER = clause("ZETA-PA-1.1")


class FakePolicyRepository(IPolicyRepository):
    async def get_payer(self, payer_id: str) -> Payer | None:
        return None

    async def list_clauses(self, payer_id: str) -> tuple[PolicyClause, ...]:
        return tuple(ACME) if payer_id == "ACME" else ()

    async def get_clause(self, clause_id: str) -> PolicyClause | None:
        return next((c for c in ACME if c.clause_id == clause_id), None)


class FixedQueryService(ICaseQueryService):
    def build(self, case_input: CaseInput, findings: Sequence[Finding]) -> str:
        return "query"


class FixedSearch(IPolicyRetrievalService):
    """Returns the given clause IDs in order, whatever is asked."""

    def __init__(self, clause_ids: Sequence[str]) -> None:
        self._clause_ids = clause_ids

    async def retrieve(self, payer_id: str, query: str, limit: int) -> tuple[RetrievedClause, ...]:
        by_id = {c.clause_id: c for c in ACME}
        return tuple(
            RetrievedClause(clause=by_id[clause_id], rank=rank, score=1.0)
            for rank, clause_id in enumerate(self._clause_ids[:limit], start=1)
        )


def service(
    found: Sequence[str], limit: int = 5, neighbour_sources: int = 0
) -> CaseRetrievalService:
    return CaseRetrievalService(
        FakePolicyRepository(),
        FixedQueryService(),
        FixedSearch(found),
        limit,
        neighbour_sources,
        document_additions=2,
    )


def finding(*clause_ids: str) -> Finding:
    return Finding(code=FindingCode.SIDE_MODIFIER_MISSING, message="m", clause_ids=clause_ids)


CASE = CaseInput.model_validate(case_input_payload())


async def test_rule_cited_clauses_come_before_search_results() -> None:
    selected = await service(["ACME-PA-1.1", "ACME-PA-2.1"]).retrieve(
        CASE, [finding("ACME-PA-2.2")]
    )

    assert [(c.clause.clause_id, c.origin) for c in selected] == [
        ("ACME-PA-2.2", ClauseOrigin.RULE),
        ("ACME-PA-1.1", ClauseOrigin.SEARCH),
        ("ACME-PA-2.1", ClauseOrigin.SEARCH),
    ]
    assert [c.rank for c in selected] == [1, 2, 3]


async def test_a_clause_found_both_ways_appears_once_as_a_rule_clause() -> None:
    selected = await service(["ACME-PA-1.1"]).retrieve(CASE, [finding("ACME-PA-1.1")])

    assert [(c.clause.clause_id, c.origin) for c in selected] == [
        ("ACME-PA-1.1", ClauseOrigin.RULE)
    ]


async def test_a_finding_cannot_bring_in_another_payers_clause() -> None:
    selected = await service(["ACME-PA-1.1"]).retrieve(CASE, [finding(OTHER.clause_id)])

    assert [c.clause.clause_id for c in selected] == ["ACME-PA-1.1"]


async def test_the_limit_caps_the_total() -> None:
    found = [c.clause_id for c in ACME]

    selected = await service(found, limit=2).retrieve(CASE, [])

    assert [c.clause.clause_id for c in selected] == ["ACME-PA-1.1", "ACME-PA-1.2"]


async def test_neighbour_is_added_after_the_first_clause_only() -> None:
    selected = await service(["ACME-PA-2.1", "ACME-PA-1.1"], neighbour_sources=1).retrieve(CASE, [])

    assert [(c.clause.clause_id, c.origin) for c in selected] == [
        ("ACME-PA-2.1", ClauseOrigin.SEARCH),
        ("ACME-PA-2.2", ClauseOrigin.NEIGHBOUR),
        ("ACME-PA-1.1", ClauseOrigin.SEARCH),
    ]


async def test_a_neighbour_already_found_lower_down_is_moved_up() -> None:
    selected = await service(
        ["ACME-PA-1.1", "ACME-PA-2.1", "ACME-PA-1.2"], neighbour_sources=1
    ).retrieve(CASE, [])

    assert [(c.clause.clause_id, c.origin) for c in selected] == [
        ("ACME-PA-1.1", ClauseOrigin.SEARCH),
        ("ACME-PA-1.2", ClauseOrigin.SEARCH),
        ("ACME-PA-2.1", ClauseOrigin.SEARCH),
    ]


async def test_the_last_clause_of_a_section_has_no_neighbour() -> None:
    selected = await service(["ACME-PA-1.2"], neighbour_sources=1).retrieve(CASE, [])

    assert [c.clause.clause_id for c in selected] == ["ACME-PA-1.2"]


def fact(document_id: str) -> NoteFact:
    return NoteFact(
        statement="The claim was accepted on time.",
        document_id=document_id,
        line_number=1,
        quote="Status: Accepted",
    )


async def selected_then_extended(
    found: Sequence[str], facts: Sequence[NoteFact]
) -> list[tuple[str, ClauseOrigin]]:
    """Select clauses with one search result, then extend with the facts given."""
    retrieval = service(found)
    first = await retrieval.retrieve(CASE, [finding("ACME-PA-1.1")])
    extended = await retrieval.extend(CASE, first, facts)
    return [(c.clause.clause_id, c.origin) for c in extended]


async def test_document_facts_add_new_clauses_after_the_ones_already_selected() -> None:
    result = await selected_then_extended(
        ["ACME-PA-1.1", "ACME-PA-2.1", "ACME-PA-2.2", "ACME-PA-1.2"], [fact("CLR")]
    )

    # The first pass kept its five-clause limit; the second adds at most two more.
    assert result[0] == ("ACME-PA-1.1", ClauseOrigin.RULE)
    assert all(origin is not ClauseOrigin.DOCUMENT for _, origin in result[:4])
    assert len({clause_id for clause_id, _ in result}) == len(result)


async def test_only_new_clauses_are_added_and_they_are_marked_as_from_documents() -> None:
    retrieval = service(["ACME-PA-2.1", "ACME-PA-2.2"])
    first = (await retrieval.retrieve(CASE, []))[:1]

    extended = await retrieval.extend(CASE, first, [fact("CLR")])

    assert [(c.clause.clause_id, c.origin, c.rank) for c in extended] == [
        ("ACME-PA-2.1", ClauseOrigin.SEARCH, 1),
        ("ACME-PA-2.2", ClauseOrigin.DOCUMENT, 2),
    ]


async def test_facts_from_the_visit_note_alone_add_nothing() -> None:
    retrieval = service(["ACME-PA-2.1", "ACME-PA-2.2"])
    first = (await retrieval.retrieve(CASE, []))[:1]

    assert await retrieval.extend(CASE, first, [fact("NOTE")]) == first
    assert await retrieval.extend(CASE, first, []) == first
