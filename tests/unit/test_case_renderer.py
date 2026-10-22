import pytest

from app.schemas.case_input import CaseInput
from app.schemas.note_fact import NoteFact
from app.utilities.case_renderer import CaseRenderer
from tests.samples import case_input_payload

FACTS = [
    NoteFact(
        statement="Prednisone 10 mg daily since 2026-04-21.",
        document_id="NOTE",
        line_number=4,
        quote="reduced to 10 mg daily on 2026-04-21",
    ),
    NoteFact(
        statement="Possible fracture.",
        document_id="DXA-REPORT",
        line_number=6,
        quote="possible fracture",
        hedged=True,
    ),
]


def test_facts_for_triage_carry_their_quotes() -> None:
    text = CaseRenderer().note_facts(FACTS)

    assert '(NOTE line 4: "reduced to 10 mg daily on 2026-04-21")' in text
    assert text.splitlines()[1].startswith("- [hedged] Possible fracture.")


def test_fact_pointers_name_the_source_line_without_repeating_the_quote() -> None:
    text = CaseRenderer().fact_pointers(FACTS)

    assert text.splitlines() == [
        "- Prednisone 10 mg daily since 2026-04-21. (NOTE line 4)",
        "- [hedged] Possible fracture. (DXA-REPORT line 6)",
    ]
    assert "reduced to" not in text


def test_no_facts_render_as_nothing_in_both_forms() -> None:
    renderer = CaseRenderer()

    assert renderer.note_facts([]) == renderer.fact_pointers([])


@pytest.mark.parametrize(
    ("quote", "clean"),
    [
        ("8| 1. Type 2 diabetes, above target.", "1. Type 2 diabetes, above target."),
        ("9|Add amlodipine 5 mg daily.", "Add amlodipine 5 mg daily."),
        # Two lines joined into one quote.
        ("right knee pain. 4| Examination: tender", "right knee pain. Examination: tender"),
        ("first line\n12| second line", "first line\nsecond line"),
        # Text that only looks like a number is left alone.
        ("Score 8|10 on the scale", "Score 8|10 on the scale"),
        ("prednisone 10 mg daily", "prednisone 10 mg daily"),
    ],
)
def test_line_numbers_copied_from_the_documents_are_removed(quote: str, clean: str) -> None:
    assert CaseRenderer().without_line_numbers(quote) == clean


def test_the_removal_undoes_the_documents_own_numbering() -> None:
    case = CaseInput.model_validate(case_input_payload())
    rendered_line = next(
        line for line in CaseRenderer().documents(case).splitlines() if line.startswith("1| ")
    )

    assert CaseRenderer().without_line_numbers(rendered_line) in case.visit_note.text
