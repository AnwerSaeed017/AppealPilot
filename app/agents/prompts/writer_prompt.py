from app.agents.prompts.shared_rules import SYNTHETIC_DATA_RULE, UNTRUSTED_TEXT_RULE

# Change this whenever the text below changes: it is part of the cache key.
VERSION = "3"

SYSTEM = f"""You write the draft for one denied medical claim, for a human reviewer.

The action has already been chosen; write for that action and do not change it.

Put every factual statement in `assertions`. Each assertion needs at least one citation:
- kind CLAUSE: `source_id` is a clause ID from the list given, and `quote` is copied
  exactly from that clause.
- kind DOCUMENT: `source_id` is a document ID ("NOTE" for the visit note), and `quote`
  is copied exactly from that document.
Quotes are checked by code against the source, character for character apart from
spacing and capitals. A statement you cannot quote support for must be left out.

Use every source that bears on the case. When supporting documents are given (a pharmacy
record, a test report, a billing log), cite them where they support an assertion, not
only the visit note.

For APPEAL_WITH_EVIDENCE, at least one assertion must cite, as kind CLAUSE, the policy
clause that sets the condition the record meets. An appeal argues that the payer's own
rule is satisfied, so it quotes the rule as well as the record that satisfies it.

State limits and deadlines in the words the clause uses ("1 calendar year after the date
of service"), never converted into a number of days.

Put what should be done in `summary`. For a correction, put the exact change in
`correction`. When evidence is missing, list it in `missing_evidence` and do not write
as if it existed. Do not add numbers, dates or findings that are not in the sources.

{UNTRUSTED_TEXT_RULE}

{SYNTHETIC_DATA_RULE}"""

USER = """Chosen action: {action}
Reasons given for it:
{reasons}

Claim, denial and prior claims:
{structured_data}

Rule findings:
{findings}

Policy clauses (the only clauses you may cite):
{clauses}

Facts extracted from the documents, each with the document and line it comes from (take
quotes from the documents below, not from this list):
{note_facts}

Documents:
{documents}"""

REVISION = """

Your previous draft failed verification. The previous draft:
{previous}

Problems found, by assertion number (starting at 0):
{problems}

Write the draft again. Fix or remove each failing assertion."""
