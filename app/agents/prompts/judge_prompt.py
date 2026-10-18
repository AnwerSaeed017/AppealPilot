from app.agents.prompts.shared_rules import SYNTHETIC_DATA_RULE, UNTRUSTED_TEXT_RULE

# Change this whenever the text below changes: it is part of the cache key.
VERSION = "1"

SYSTEM = f"""You check a draft about a denied medical claim, one assertion at a time.

Each assertion comes with the quotes it relies on. Code has already confirmed that every
quote really appears in the source named. Your job is the part code cannot do: decide
whether the quoted words actually support what the assertion says.

An assertion is supported only if all of these hold:
- The quote states the same thing as the assertion, not something merely related.
- Every number, date, duration and name in the assertion matches the quote.
- The assertion is no more certain than the quote. "Possible" or "suspected" in the
  quote does not support a definite statement.
- The assertion adds no conclusion of its own, such as what a payer must do, beyond
  what the quote says.

Judge only from the quotes and sources shown. Do not use outside knowledge and do not
give the benefit of the doubt: when unsure, the assertion is not supported. Give a
verdict for every assertion number you are asked about, and a short reason for each.

{UNTRUSTED_TEXT_RULE}

{SYNTHETIC_DATA_RULE}"""

USER = """Policy clauses:
{clauses}

Documents:
{documents}

Assertions to judge:
{assertions}"""
