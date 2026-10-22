from typing import Any

from app.schemas.case_clause import CaseClause, ClauseOrigin
from app.schemas.case_input import CaseInput
from app.schemas.draft import Draft
from app.schemas.policy_clause import PolicyClause
from app.schemas.verification_report import VerificationReport
from app.services.citation_verifier_service import CitationVerifierService
from app.utilities.quote_matcher import QuoteMatcher
from tests.samples import case_input_payload, policy_clause_payload

CASE = CaseInput.model_validate(case_input_payload())
CLAUSE = PolicyClause.model_validate(policy_clause_payload())
SELECTED = [CaseClause(clause=CLAUSE, rank=1, origin=ClauseOrigin.SEARCH)]


def draft_with(*citations: dict[str, Any]) -> Draft:
    return Draft.model_validate(
        {
            "action": "APPEAL_WITH_EVIDENCE",
            "summary": "Appeal.",
            "assertions": [{"text": "A statement.", "citations": list(citations)}],
        }
    )


async def check(*citations: dict[str, Any]) -> VerificationReport:
    return CitationVerifierService(QuoteMatcher()).check(draft_with(*citations), CASE, SELECTED)


async def test_real_quotes_from_a_clause_and_the_note_pass() -> None:
    report = await check(
        {"kind": "CLAUSE", "source_id": "ACME-PA-4.2", "quote": "may be reconsidered"},
        {"kind": "DOCUMENT", "source_id": "NOTE", "quote": "Authorization obtained by phone"},
    )

    assert report.passed
    assert report.verdicts[0].problems == ()


async def test_spacing_line_breaks_and_capitals_are_ignored() -> None:
    report = await check(
        {
            "kind": "DOCUMENT",
            "source_id": "NOTE",
            # The note has a line break between these two sentences.
            "quote": "performed  TODAY. authorization obtained",
        }
    )

    assert report.passed


async def test_a_quote_that_is_not_in_the_source_fails() -> None:
    report = await check(
        {"kind": "CLAUSE", "source_id": "ACME-PA-4.2", "quote": "must always be paid in full"}
    )

    assert not report.passed
    assert "is not in ACME-PA-4.2" in report.verdicts[0].problems[0]


async def test_a_changed_number_in_a_quote_fails() -> None:
    report = await check(
        {
            "kind": "DOCUMENT",
            "source_id": "NOTE",
            "quote": "Authorization obtained by phone on 2026-05-30",
        }
    )

    assert not report.passed


async def test_a_clause_that_was_not_selected_fails_even_if_it_exists() -> None:
    report = CitationVerifierService(QuoteMatcher()).check(
        draft_with({"kind": "CLAUSE", "source_id": "ACME-PA-4.2", "quote": "may be reconsidered"}),
        CASE,
        [],
    )

    assert "was not selected for this case" in report.verdicts[0].problems[0]


async def test_an_unknown_document_fails() -> None:
    report = await check({"kind": "DOCUMENT", "source_id": "MEMO", "quote": "anything"})

    assert "is not part of this case" in report.verdicts[0].problems[0]


async def test_one_bad_citation_fails_the_assertion_and_names_only_that_one() -> None:
    report = await check(
        {"kind": "CLAUSE", "source_id": "ACME-PA-4.2", "quote": "may be reconsidered"},
        {"kind": "CLAUSE", "source_id": "ACME-PA-9.9", "quote": "invented"},
    )

    assert not report.passed
    assert len(report.verdicts[0].problems) == 1
    assert "ACME-PA-9.9" in report.verdicts[0].problems[0]


async def test_a_draft_with_no_assertions_passes() -> None:
    draft = Draft.model_validate({"action": "NO_ACTION", "summary": "Nothing to do."})

    assert (CitationVerifierService(QuoteMatcher()).check(draft, CASE, SELECTED)).passed


TYPED_NOTE = CASE.model_copy(
    update={
        "visit_note": CASE.visit_note.model_copy(
            update={"text": 'Intra-articular injection; glucose 180-240 mg/dL. The "left" knee.'}
        )
    }
)
# Typographic forms models write, built from code points so the file stays plain ASCII.
NON_BREAKING_HYPHEN = chr(0x2011)
EN_DASH = chr(0x2013)
LEFT_DOUBLE_QUOTE = chr(0x201C)
RIGHT_DOUBLE_QUOTE = chr(0x201D)


async def test_typographic_hyphens_dashes_and_quotes_match_their_plain_forms() -> None:
    # The note has plain ASCII; the quote has a non-breaking hyphen, an en dash and curly
    # double quotes. The words are the same, so the quote is faithful.
    quote = (
        f"Intra{NON_BREAKING_HYPHEN}articular injection; glucose 180{EN_DASH}240 mg/dL. "
        f"The {LEFT_DOUBLE_QUOTE}left{RIGHT_DOUBLE_QUOTE} knee."
    )
    draft = draft_with({"kind": "DOCUMENT", "source_id": "NOTE", "quote": quote})

    report = CitationVerifierService(QuoteMatcher()).check(draft, TYPED_NOTE, SELECTED)

    assert report.passed


async def test_typography_never_excuses_a_changed_word() -> None:
    quote = f"Intra{NON_BREAKING_HYPHEN}articular injection; glucose 180{EN_DASH}250 mg/dL"
    draft = draft_with({"kind": "DOCUMENT", "source_id": "NOTE", "quote": quote})

    report = CitationVerifierService(QuoteMatcher()).check(draft, TYPED_NOTE, SELECTED)

    assert not report.passed


async def test_a_quote_joining_separate_sentences_is_explained() -> None:
    # Both sentences are in the note, but not next to each other.
    joined = "Established patient seen for right knee pain. Authorization obtained by phone"

    report = await check({"kind": "DOCUMENT", "source_id": "NOTE", "quote": joined})

    assert not report.passed
    assert "joins passages that are not next to each other" in report.verdicts[0].problems[0]


async def test_a_quote_shortened_with_an_ellipsis_is_explained() -> None:
    shortened = "A claim denied for absent authorization ... issued before the date of service."

    report = await check({"kind": "CLAUSE", "source_id": "ACME-PA-4.2", "quote": shortened})

    assert "in its own citation" in report.verdicts[0].problems[0]


async def test_an_invented_passage_gets_the_plain_message() -> None:
    invented = (
        "Established patient seen for right knee pain. The injection was medically necessary."
    )

    report = await check({"kind": "DOCUMENT", "source_id": "NOTE", "quote": invented})

    assert report.verdicts[0].problems[0].endswith("is not in NOTE")


async def test_an_added_or_dropped_comma_changes_no_word() -> None:
    # The clause has "may be reconsidered when the provider supplies"; a model adds a comma.
    report = await check(
        {
            "kind": "CLAUSE",
            "source_id": "ACME-PA-4.2",
            "quote": "may be reconsidered, when the provider supplies",
        }
    )

    assert report.passed


async def test_a_comma_never_excuses_a_changed_word_or_number() -> None:
    report = await check(
        {
            "kind": "CLAUSE",
            "source_id": "ACME-PA-4.2",
            "quote": "may be reconsidered, when the provider requests",
        },
        {
            "kind": "DOCUMENT",
            "source_id": "NOTE",
            "quote": "Authorization obtained by phone on 2026-05-30",
        },
    )

    assert [verdict.supported for verdict in report.verdicts] == [False]
