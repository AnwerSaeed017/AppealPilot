"""Would adding embeddings to the keyword search be worth its cost?

    uv sync --all-packages --group bench
    uv run python -m scripts.benchmarks.embedding_benchmark

Measures, on the development cases only:
  - recall of keyword search, embeddings alone, and the two combined by rank;
  - the memory and time that loading the embedding model adds.

Nothing here is used by the application. If the numbers justify embeddings, they get
wired in properly; if not, this script is the record of why they were left out.
"""

import asyncio
import os
import time
from collections.abc import Sequence

import numpy as np
import psutil
from dependency_injector import providers
from fastembed import TextEmbedding

from app.containers.container import Container
from app.core.settings import Settings
from app.interfaces.repository.policy_repository import IPolicyRepository
from app.interfaces.service.policy_retrieval_service import IPolicyRetrievalService
from app.schemas.policy_clause import PolicyClause
from app.schemas.retrieved_clause import RetrievedClause
from app.services.case_retrieval_service import CaseRetrievalService
from tests.evals.retrieval_report import CUT_OFFS, load_dev_cases

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
RANK_FUSION_CONSTANT = 60
LIMIT = max(CUT_OFFS)
NEIGHBOUR_SOURCES = 1


def memory_mb() -> float:
    return psutil.Process(os.getpid()).memory_info().rss / 1_048_576


class EmbeddingRetrieval(IPolicyRetrievalService):
    """Ranks a payer's clauses by cosine similarity to the query."""

    def __init__(self, repository: IPolicyRepository, model: TextEmbedding) -> None:
        self._repository = repository
        self._model = model
        self._payers: dict[str, tuple[tuple[PolicyClause, ...], np.ndarray]] = {}

    async def prepare(self, payer_ids: Sequence[str]) -> int:
        """Embed every clause of the given payers. Returns how many were embedded."""
        count = 0
        for payer_id in payer_ids:
            clauses = await self._repository.list_clauses(payer_id)
            texts = [f"{c.policy_title}. {c.section_heading}. {c.text}" for c in clauses]
            self._payers[payer_id] = (clauses, self._normalised(texts))
            count += len(clauses)
        return count

    async def retrieve(self, payer_id: str, query: str, limit: int) -> tuple[RetrievedClause, ...]:
        clauses, vectors = self._payers[payer_id]
        similarities = vectors @ self._normalised([query])[0]
        order = np.argsort(-similarities)[:limit]
        return tuple(
            # Shifted above zero only because the schema requires a positive score.
            RetrievedClause(clause=clauses[i], rank=rank, score=float(similarities[i]) + 2.0)
            for rank, i in enumerate(order, start=1)
        )

    def _normalised(self, texts: Sequence[str]) -> np.ndarray:
        vectors = np.array(list(self._model.embed(list(texts))))
        return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)


class RankFusionRetrieval(IPolicyRetrievalService):
    """Combines two searches by reciprocal rank fusion."""

    def __init__(self, first: IPolicyRetrievalService, second: IPolicyRetrievalService) -> None:
        self._searches = (first, second)

    async def retrieve(self, payer_id: str, query: str, limit: int) -> tuple[RetrievedClause, ...]:
        scores: dict[str, float] = {}
        clauses: dict[str, PolicyClause] = {}
        for search in self._searches:
            # Ask each search for every clause, so a low rank in one still counts.
            for found in await search.retrieve(payer_id, query, 1000):
                clauses[found.clause.clause_id] = found.clause
                scores[found.clause.clause_id] = scores.get(found.clause.clause_id, 0.0) + 1 / (
                    RANK_FUSION_CONSTANT + found.rank
                )
        best = sorted(scores, key=lambda clause_id: -scores[clause_id])[:limit]
        return tuple(
            RetrievedClause(clause=clauses[clause_id], rank=rank, score=scores[clause_id])
            for rank, clause_id in enumerate(best, start=1)
        )


async def recall(container: Container, search: IPolicyRetrievalService) -> dict[int, list[int]]:
    """[any found, all found, clauses found, clauses] at each cut-off."""
    selection = CaseRetrievalService(
        container.repositories.policy_repository(),
        container.services.case_query_service(),
        search,
        LIMIT,
        NEIGHBOUR_SOURCES,
        document_additions=0,
    )
    engine = container.services.rules_engine_service()
    totals = {cut_off: [0, 0, 0, 0] for cut_off in CUT_OFFS}
    for case in load_dev_cases():
        case_input = case.case_input()
        findings = await engine.evaluate(case_input, case.as_of_date)
        ordered = [c.clause.clause_id for c in await selection.retrieve(case_input, findings)]
        expected = set(case.expected.relevant_clause_ids)
        for cut_off in CUT_OFFS:
            hits = expected & set(ordered[:cut_off])
            totals[cut_off][0] += bool(hits)
            totals[cut_off][1] += hits == expected
            totals[cut_off][2] += len(hits)
            totals[cut_off][3] += len(expected)
    return totals


async def main() -> None:
    container = Container()
    container.settings.override(providers.Object(Settings(_env_file=None)))
    repository = container.repositories.policy_repository()
    keyword = container.services.policy_retrieval_service()
    await keyword.retrieve("TESS", "warm up", 1)
    await keyword.retrieve("QUIL", "warm up", 1)

    memory_before = memory_mb()
    started = time.perf_counter()
    model = TextEmbedding(MODEL_NAME)
    load_seconds = time.perf_counter() - started

    embeddings = EmbeddingRetrieval(repository, model)
    started = time.perf_counter()
    clause_count = await embeddings.prepare(["TESS", "QUIL"])
    embed_seconds = time.perf_counter() - started
    memory_after = memory_mb()

    started = time.perf_counter()
    for _ in range(20):
        await embeddings.retrieve("TESS", "prior authorization absent procedure code 73721", 5)
    query_ms = (time.perf_counter() - started) / 20 * 1000

    print(f"Model: {MODEL_NAME}")
    print(f"Model load (files already downloaded): {load_seconds:.2f} s")
    print(f"Embedding {clause_count} clauses: {embed_seconds:.2f} s")
    print(f"One embedding search: {query_ms:.1f} ms")
    print(
        f"Process memory: {memory_before:.0f} MB before, {memory_after:.0f} MB after "
        f"(+{memory_after - memory_before:.0f} MB)"
    )
    print()
    print("| Search | Top | Any labelled clause | All | Clauses |")
    print("|---|---|---|---|---|")
    searches: dict[str, IPolicyRetrievalService] = {
        "Keyword (in use)": keyword,
        "Embeddings alone": embeddings,
        "Keyword + embeddings": RankFusionRetrieval(keyword, embeddings),
    }
    cases = len(load_dev_cases())
    for name, search in searches.items():
        for cut_off, (any_found, all_found, found, total) in (
            await recall(container, search)
        ).items():
            print(
                f"| {name} | {cut_off} | {any_found} of {cases} | {all_found} of {cases} "
                f"| {found} of {total} |"
            )


if __name__ == "__main__":
    asyncio.run(main())
