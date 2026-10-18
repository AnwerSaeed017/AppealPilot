from abc import ABC, abstractmethod
from datetime import datetime


class IClock(ABC):
    @abstractmethod
    def now(self) -> datetime:
        """The current time as a timezone-aware UTC datetime."""
