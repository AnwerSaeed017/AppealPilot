import re

from app.constants.retrieval import MIN_LENGTH_FOR_PLURAL_STRIPPING, STOPWORDS
from app.interfaces.utilities.text_tokenizer import ITextTokenizer

_WORD = re.compile(r"[a-z0-9]+")


class WordTokenizer(ITextTokenizer):
    """Lower-cased words and codes, without stopwords, with a plain plural "s" removed.

    Codes such as 73721 or J7325 survive intact, which is what lets a claim's procedure
    code find the clause that names it.
    """

    def tokenize(self, text: str) -> tuple[str, ...]:
        return tuple(
            self._singular(word) for word in _WORD.findall(text.lower()) if word not in STOPWORDS
        )

    @staticmethod
    def _singular(word: str) -> str:
        is_plural = (
            len(word) >= MIN_LENGTH_FOR_PLURAL_STRIPPING
            and word.endswith("s")
            and not word.endswith("ss")
            and not word.isdigit()
        )
        return word[:-1] if is_plural else word
