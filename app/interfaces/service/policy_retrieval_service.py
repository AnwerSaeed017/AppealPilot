from abc import ABC, abstractmethod

from app.schemas.retrieved_clause import RetrievedClause


class IPolicyRetrievalService(ABC):
    @abstractmethod
    async def retrieve(self, payer_id: str, query: str, limit: int) -> tuple[RetrievedClause, ...]:
        """The best-matching clauses of one payer, best first, at most `limit`.

        Only that payer's clauses are searched. Clauses with no term in common with the
        query are left out, so fewer than `limit` may come back.
        """
