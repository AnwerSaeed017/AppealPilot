from app.constants.text import TYPOGRAPHIC_EQUIVALENTS
from app.interfaces.utilities.quote_matcher import IQuoteMatcher


class QuoteMatcher(IQuoteMatcher):
    def contains(self, source: str, quote: str) -> bool:
        needle = self._normalised(quote)
        return bool(needle) and needle in self._normalised(source)

    @staticmethod
    def _normalised(text: str) -> str:
        return " ".join(text.translate(TYPOGRAPHIC_EQUIVALENTS).split()).casefold()
