from collections.abc import Sequence

from app.interfaces.repository.policy_repository import IPolicyRepository
from app.interfaces.service.case_query_service import ICaseQueryService
from app.interfaces.service.case_retrieval_service import ICaseRetrievalService
from app.interfaces.service.policy_retrieval_service import IPolicyRetrievalService
from app.schemas.case_clause import CaseClause, ClauseOrigin
from app.schemas.case_input import CaseInput
from app.schemas.code_types import VISIT_NOTE_DOCUMENT_ID
from app.schemas.finding import Finding
from app.schemas.note_fact import NoteFact
from app.schemas.policy_clause import PolicyClause


class CaseRetrievalService(ICaseRetrievalService):
    """Selects the clauses for a case from three sources, in this order of trust.

    1. Clauses that rule findings cite. These are certain, so they come first.
    2. Clauses the search matched, best first.
    3. For the first few of those, the clause that follows in the same section. A
       policy often states a requirement in one clause and what to do about it in the
       next, and the denial's wording matches only the first.
    """

    def __init__(
        self,
        policy_repository: IPolicyRepository,
        case_query_service: ICaseQueryService,
        policy_retrieval_service: IPolicyRetrievalService,
        limit: int,
        neighbour_sources: int,
        document_additions: int,
    ) -> None:
        self._policy_repository = policy_repository
        self._case_query_service = case_query_service
        self._policy_retrieval_service = policy_retrieval_service
        self._limit = limit
        self._neighbour_sources = neighbour_sources
        self._document_additions = document_additions

    async def retrieve(
        self, case_input: CaseInput, findings: Sequence[Finding]
    ) -> tuple[CaseClause, ...]:
        payer_id = case_input.claim.payer_id
        payer_clauses = await self._policy_repository.list_clauses(payer_id)
        by_id = {clause.clause_id: clause for clause in payer_clauses}

        selected: dict[str, tuple[PolicyClause, ClauseOrigin]] = {}
        for finding in findings:
            for clause_id in finding.clause_ids:
                # A finding can only cite the payer's own clauses; anything else is dropped.
                if clause_id in by_id:
                    selected.setdefault(clause_id, (by_id[clause_id], ClauseOrigin.RULE))

        query = self._case_query_service.build(case_input, findings)
        for found in await self._policy_retrieval_service.retrieve(payer_id, query, self._limit):
            selected.setdefault(found.clause.clause_id, (found.clause, ClauseOrigin.SEARCH))

        ordered = self._with_neighbours(list(selected.values()), payer_clauses)
        return tuple(
            CaseClause(clause=clause, rank=rank, origin=origin)
            for rank, (clause, origin) in enumerate(ordered[: self._limit], start=1)
        )

    async def extend(
        self,
        case_input: CaseInput,
        clauses: Sequence[CaseClause],
        note_facts: Sequence[NoteFact],
        findings: Sequence[Finding],
    ) -> tuple[CaseClause, ...]:
        clauses = await self._with_cited_clauses(case_input, clauses, findings)
        # A billing note or a report can show that a different clause applies than the
        # denial suggests. The visit note is left out: it describes the care, and the
        # first search already covers the procedure.
        document_facts = [fact for fact in note_facts if fact.document_id != VISIT_NOTE_DOCUMENT_ID]
        if not document_facts or self._document_additions == 0:
            return tuple(clauses)

        query = "\n".join(f"{fact.statement} {fact.quote}" for fact in document_facts)
        already = {item.clause.clause_id for item in clauses}
        found = await self._policy_retrieval_service.retrieve(
            case_input.claim.payer_id, query, self._limit + len(already)
        )
        new = [item.clause for item in found if item.clause.clause_id not in already]
        added = tuple(
            CaseClause(clause=clause, rank=len(clauses) + position, origin=ClauseOrigin.DOCUMENT)
            for position, clause in enumerate(new[: self._document_additions], start=1)
        )
        return (*clauses, *added)

    async def _with_cited_clauses(
        self, case_input: CaseInput, clauses: Sequence[CaseClause], findings: Sequence[Finding]
    ) -> tuple[CaseClause, ...]:
        """The clauses, plus any of the payer's clauses a finding cites that are missing."""
        payer_clauses = await self._policy_repository.list_clauses(case_input.claim.payer_id)
        by_id = {clause.clause_id: clause for clause in payer_clauses}
        selected = {item.clause.clause_id for item in clauses}
        added: list[CaseClause] = []
        for finding in findings:
            for clause_id in finding.clause_ids:
                if clause_id in by_id and clause_id not in selected:
                    selected.add(clause_id)
                    added.append(
                        CaseClause(
                            clause=by_id[clause_id],
                            rank=len(clauses) + len(added) + 1,
                            origin=ClauseOrigin.RULE,
                        )
                    )
        return (*clauses, *added)

    def _with_neighbours(
        self,
        ordered: list[tuple[PolicyClause, ClauseOrigin]],
        payer_clauses: Sequence[PolicyClause],
    ) -> list[tuple[PolicyClause, ClauseOrigin]]:
        """Place, after each of the first few clauses, the next clause of its section.

        A neighbour that was already selected further down is moved up and keeps its
        origin. One that was not selected is added as a neighbour.
        """
        origins = {clause.clause_id: origin for clause, origin in ordered}
        placed: set[str] = set()
        result: list[tuple[PolicyClause, ClauseOrigin]] = []
        for position, (clause, origin) in enumerate(ordered):
            if clause.clause_id in placed:
                continue
            placed.add(clause.clause_id)
            result.append((clause, origin))
            if position >= self._neighbour_sources:
                continue
            neighbour = self._next_in_section(clause, payer_clauses)
            if neighbour is not None and neighbour.clause_id not in placed:
                placed.add(neighbour.clause_id)
                result.append((neighbour, origins.get(neighbour.clause_id, ClauseOrigin.NEIGHBOUR)))
        return result

    @staticmethod
    def _next_in_section(
        clause: PolicyClause, payer_clauses: Sequence[PolicyClause]
    ) -> PolicyClause | None:
        """The clause after this one, if it shares the section (4.1 and 4.2, not 5.1)."""
        index = payer_clauses.index(clause)
        if index + 1 >= len(payer_clauses):
            return None
        following = payer_clauses[index + 1]
        same_section = following.clause_id.rsplit(".", 1)[0] == clause.clause_id.rsplit(".", 1)[0]
        return following if same_section else None
