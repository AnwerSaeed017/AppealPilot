from abc import ABC, abstractmethod
from typing import Any


class IDateShifter(ABC):
    @abstractmethod
    def shift(self, value: Any, days: int) -> Any:
        """A copy of a JSON-like value with every ISO date in it moved by `days`.

        Dates inside free text move too, so a note and its claim keep agreeing.
        """
