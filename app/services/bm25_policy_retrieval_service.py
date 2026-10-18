from app.interfaces.repository.policy_repository import IPolicyRepository
from app.interfaces.service.policy_retrieval_service import IPolicyRetrievalService
from app.interfaces.utilities.text_scorer import ITextScorer
from app.interfaces.utilities.text_tokenizer import ITextTokenizer
from app.schemas.policy_clause import PolicyClause
from app.schemas.retrieved_clause import RetrievedClause

# One payer's clauses beside their search terms, in the same order.
_Corpus = tuple[tuple[PolicyClause, ...], tuple[tuple[str, ...], ...]]


class Bm25PolicyRetrievalService(IPolicyRetrievalService):
    """Keyword search over one payer's clauses.

    A payer's clauses are tokenised on first use and kept. The policies change only
    with a deployment, so every process holds the same terms.
    """

    def __init__(
        self,
        policy_repository: IPolicyRepository,
        tokenizer: ITextTokenizer,
        scorer: ITextScorer,
    ) -> None:
        self._policy_repository = policy_repository
        self._tokenizer = tokenizer
        self._scorer = scorer
        self._corpora: dict[str, _Corpus] = {}

    async def retrieve(self, payer_id: str, query: str, limit: int) -> tuple[RetrievedClause, ...]:
        clauses, documents = await self._corpus_for(payer_id)
        scores = self._scorer.score(documents, self._tokenizer.tokenize(query))
        # Sorting is stable, so clauses with equal scores keep their policy order.
        ranked = sorted(zip(clauses, scores, strict=True), key=lambda pair: -pair[1])
        return tuple(
            RetrievedClause(clause=clause, rank=rank, score=score)
            for rank, (clause, score) in enumerate(ranked[: max(limit, 0)], start=1)
            if score > 0
        )

    async def _corpus_for(self, payer_id: str) -> _Corpus:
        if payer_id not in self._corpora:
            clauses = await self._policy_repository.list_clauses(payer_id)
            documents = tuple(
                self._tokenizer.tokenize(self._searchable_text(clause)) for clause in clauses
            )
            self._corpora[payer_id] = (clauses, documents)
        return self._corpora[payer_id]

    @staticmethod
    def _searchable_text(clause: PolicyClause) -> str:
        return f"{clause.policy_title}\n{clause.section_heading}\n{clause.text}"
