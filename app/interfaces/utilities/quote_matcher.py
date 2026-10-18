from abc import ABC, abstractmethod


class IQuoteMatcher(ABC):
    """Decides whether a quote really appears in a source text."""

    @abstractmethod
    def contains(self, source: str, quote: str) -> bool:
        """True when the quote is in the source, ignoring only spacing, line breaks,
        capitals and typography (dashes, curly quotes). Every word must match."""
