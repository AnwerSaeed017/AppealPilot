import math
from collections import Counter
from collections.abc import Sequence

from app.constants.retrieval import BM25_LENGTH_NORMALISATION, BM25_TERM_SATURATION
from app.interfaces.utilities.text_scorer import ITextScorer


class Bm25Scorer(ITextScorer):
    """Okapi BM25. Holds nothing between calls: the documents come in with each query."""

    def score(self, documents: Sequence[Sequence[str]], query: Sequence[str]) -> list[float]:
        if not documents:
            return []
        term_counts = [Counter(document) for document in documents]
        average_length = sum(len(document) for document in documents) / len(documents)

        # Each query term counts once, however often the query repeats it.
        weights = {term: self._rarity(term, term_counts) for term in dict.fromkeys(query) if term}
        return [
            sum(
                weight * self._saturated(counts[term], len(document), average_length)
                for term, weight in weights.items()
                if counts[term]
            )
            for document, counts in zip(documents, term_counts, strict=True)
        ]

    @staticmethod
    def _rarity(term: str, term_counts: Sequence[Counter[str]]) -> float:
        """Inverse document frequency: a term found in few documents weighs more."""
        containing = sum(1 for counts in term_counts if term in counts)
        return math.log(1 + (len(term_counts) - containing + 0.5) / (containing + 0.5))

    @staticmethod
    def _saturated(frequency: int, length: int, average_length: float) -> float:
        """Term frequency with diminishing returns, adjusted for document length."""
        length_factor = (
            1
            - BM25_LENGTH_NORMALISATION
            + BM25_LENGTH_NORMALISATION * length / (average_length or 1)
        )
        return (
            frequency
            * (BM25_TERM_SATURATION + 1)
            / (frequency + BM25_TERM_SATURATION * length_factor)
        )
