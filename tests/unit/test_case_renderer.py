from app.schemas.note_fact import NoteFact
from app.utilities.case_renderer import CaseRenderer

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
