from abc import ABC, abstractmethod
from collections.abc import Sequence


class ITextScorer(ABC):
    @abstractmethod
    def score(self, documents: Sequence[Sequence[str]], query: Sequence[str]) -> list[float]:
        """How well each tokenised document matches the tokenised query.

        Returns one score per document, in the order given. A document that shares no
        term with the query scores 0.
        """
