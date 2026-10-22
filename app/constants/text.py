"""Characters that differ in print but not in meaning.

Models often write typographic forms where the source has the plain ASCII one: a
non-breaking hyphen in "intra-articular", an en dash in "180-240", curly quote marks. A
quote is compared after mapping each of these to its plain form, so a faithful quote is
never rejected for its typography or a comma. Nothing that changes a word is mapped.
"""

import re

# Each plain form, with the code points written instead of it.
_PLAIN_FORMS: dict[str, tuple[int, ...]] = {
    # Hyphens, dashes and minus signs.
    "-": (0x2010, 0x2011, 0x2012, 0x2013, 0x2014, 0x2015, 0x2212, 0xFE58, 0xFE63, 0xFF0D),
    # Single quotes, apostrophes and the prime.
    "'": (0x2018, 0x2019, 0x201A, 0x201B, 0x2032),
    # Double quotes and the double prime.
    '"': (0x201C, 0x201D, 0x201E, 0x201F, 0x2033),
    # The ellipsis character.
    "...": (0x2026,),
    # Zero-width characters, which only affect layout.
    "": (0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF),
    # The comma, read as a space: a model often adds or drops one ("not limited to, the"),
    # which changes no word. Words and numbers must still match exactly.
    " ": (0x002C,),
}

# For str.translate: code point to its plain form.
TYPOGRAPHIC_EQUIVALENTS: dict[int, str] = {
    code: plain for plain, codes in _PLAIN_FORMS.items() for code in codes
}

# Where a quote may be split into the passages it was built from: after the end of a
# sentence or clause, or at an ellipsis a model used to shorten it.
PASSAGE_BREAK = re.compile(r"(?<=[.;:])\s+|\s*(?:\.\.\.|…)\s*")
