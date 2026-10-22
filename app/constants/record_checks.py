"""Patterns the record checks look for in the quoted words of extracted facts."""

import re

# A side of the body, as a whole word.
SIDE_WORD = re.compile(r"\b(left|right)\b", re.IGNORECASE)

# A stated age: "7-year-old", "72 year old".
STATED_AGE = re.compile(r"\b(\d{1,3})[- ]year[- ]old\b", re.IGNORECASE)

# A line of a clearinghouse or plan report saying the payer accepted the claim, and one
# saying it did not. A report with both is not taken as proof of acceptance.
ACCEPTED_WORDING = re.compile(r"\baccepted\b", re.IGNORECASE)
REJECTED_WORDING = re.compile(r"\b(rejected|not accepted|denied)\b", re.IGNORECASE)

# A stated age further than this from the age the claim's date of birth gives is a
# different person, not a rounding of the same one.
AGE_TOLERANCE_YEARS = 1
