from abc import ABC, abstractmethod


class IHealthRepository(ABC):
    @abstractmethod
    async def is_database_reachable(self) -> bool:
        """True when a trivial query succeeds. Never raises for a database failure."""
