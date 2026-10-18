"""Settings of the keyword search over policy clauses that do not vary by environment."""

# Okapi BM25 parameters, at their usual values.
BM25_TERM_SATURATION = 1.5
BM25_LENGTH_NORMALISATION = 0.75

# Words too common to help tell one clause from another.
STOPWORDS: frozenset[str] = frozenset(
    {
        "a", "an", "and", "any", "are", "as", "at", "be", "been", "but", "by", "for", "from",
        "has", "have", "in", "is", "it", "its", "may", "must", "no", "not", "of", "on", "or",
        "that", "the", "their", "this", "to", "was", "were", "when", "which", "with", "without",
    }
)  # fmt: skip

# Plural endings are removed only from words at least this long, so "has" stays "has".
MIN_LENGTH_FOR_PLURAL_STRIPPING = 4
