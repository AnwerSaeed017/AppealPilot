from abc import ABC, abstractmethod

from app.schemas.payer import Payer
from app.schemas.policy_clause import PolicyClause


class IPolicyRepository(ABC):
    """Read access to payers and their policy clauses."""

    @abstractmethod
    async def get_payer(self, payer_id: str) -> Payer | None:
        """The payer, or None when it is not known."""

    @abstractmethod
    async def list_clauses(self, payer_id: str) -> tuple[PolicyClause, ...]:
        """Every clause of one payer, in a stable order. Empty for an unknown payer."""

    @abstractmethod
    async def get_clause(self, clause_id: str) -> PolicyClause | None:
        """The clause, or None when no policy defines it."""
