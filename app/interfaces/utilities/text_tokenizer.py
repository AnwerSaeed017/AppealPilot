from abc import ABC, abstractmethod


class ITextTokenizer(ABC):
    @abstractmethod
    def tokenize(self, text: str) -> tuple[str, ...]:
        """The search terms in `text`, in order, normalised so that equal terms match."""
