"""Denials for a missing or inconsistent modifier (reason code 4)."""

from datetime import timedelta
from typing import Any

from app.schemas.recommended_action import RecommendedAction
from tests.evals.generator.kit import Built, Doc, Kit
from tests.evals.generator.payer_rules import PayerRules

# --- Side modifiers ----------------------------------------------------------


def _injection_note(kit: Kit, history_side: str | None, procedure_side: str | None) -> Doc:
    """A knee injection note. A side of None leaves that part of the note silent."""
    note = kit.note(f"{history_side} knee pain" if history_side else "knee pain")
    if history_side:
        note.add(
            f"History: osteoarthritis of the {history_side} knee; "
            + kit.pick("pain worse on stairs.", "pain wakes the patient at night."),
            "history_side",
        )
    else:
        note.add("History: osteoarthritis of the knee; pain worse on stairs.")
    note.add("Examination: crepitus and a small effusion.")
    if procedure_side:
        note.add(
            kit.pick(
                f"Procedure: {procedure_side} knee aspirated and injected with corticosteroid.",
                f"Procedure: corticosteroid injection into the {procedure_side} knee joint "
                "after aspiration.",
            ),
            "procedure_side",
        )
    else:
        note.add("Procedure: knee aspirated and injected with corticosteroid.", "no_side")
    note.add("Plan: review in six weeks.")
    return kit.sign(note)


def _injection_claim(kit: Kit, modifiers: tuple[str, ...], diagnosis: str) -> dict[str, Any]:
    return kit.claim([kit.line(1, "20610", modifiers=modifiers)], (diagnosis,))


def _shorthand_injection_note(kit: Kit) -> Doc:
    """The same visit as a clinician in a hurry writes it: "R knee", not "right knee"."""
    letter = "R" if kit.side == "right" else "L"
    note = kit.note(f"{letter} knee pain")
    note.add(f"Hx: OA {letter} knee, worse on stairs.")
    note.add("O/E: crepitus, small effusion.")
    note.add(f"Proc: {letter} knee aspirated + injected w/ corticosteroid.", "procedure_side")
    note.add("Plan: r/v 6/52.")
    return kit.sign(note)


def side_missing_documented(kit: Kit, rules: PayerRules, shorthand: bool = False) -> Built:
    """No side modifier on the claim; the note states the side."""
    note = _shorthand_injection_note(kit) if shorthand else _injection_note(kit, kit.side, kit.side)
    claim = _injection_claim(kit, (), kit.knee_oa_code)

    return Built(
        input=kit.case_input(claim, kit.denial(claim, "4"), note),
        as_of_date=kit.as_of,
        action=RecommendedAction.CORRECT_AND_RESUBMIT,
        clauses=(rules.side_modifier, rules.side_modifier_fix, rules.corrected_claim_limit),
        evidence=note.refs("procedure_side"),
        correction=f"Add modifier {kit.side_modifier} to line 1 and send a corrected claim.",
        rationale=(
            f"The note for the date of service says the {kit.side} knee was injected, and "
            f"the corrected claim is still inside the {rules.corrected_claim_days}-day limit."
        ),
    )


def side_wrong(kit: Kit, rules: PayerRules) -> Built:
    """The claim names one side; the note says the other."""
    wrong_modifier = "LT" if kit.side == "right" else "RT"
    note = _injection_note(kit, kit.side, kit.side)
    claim = _injection_claim(kit, (wrong_modifier,), kit.knee_oa_code)

    return Built(
        input=kit.case_input(claim, kit.denial(claim, "4"), note),
        as_of_date=kit.as_of,
        action=RecommendedAction.CORRECT_AND_RESUBMIT,
        clauses=(rules.side_modifier, rules.side_modifier_fix, rules.corrected_claim_limit),
        evidence=note.refs("history_side", "procedure_side"),
        correction=(
            f"Replace modifier {wrong_modifier} with {kit.side_modifier} on line 1 "
            "and send a corrected claim."
        ),
        rationale=(
            f"The claim was billed with {wrong_modifier}, but the note consistently "
            f"describes the {kit.side} knee, and the diagnosis code agrees with the note."
        ),
    )


def side_not_recorded(kit: Kit, rules: PayerRules) -> Built:
    """Neither the claim nor the note says which knee."""
    note = _injection_note(kit, None, None)
    claim = _injection_claim(kit, (), "M17.10")

    return Built(
        input=kit.case_input(claim, kit.denial(claim, "4"), note),
        as_of_date=kit.as_of,
        action=RecommendedAction.REQUEST_DOCUMENTATION,
        clauses=(rules.side_modifier_fix,),
        evidence=note.refs("no_side"),
        missing=("dated addendum from the treating clinician stating which knee was injected",),
        rationale=(
            "A side modifier is required, but the note never says which knee and the "
            "diagnosis code is the unspecified-side one. The policy forbids guessing: an "
            "addendum from the clinician comes first."
        ),
    )


def side_contradiction(kit: Kit, rules: PayerRules) -> Built:
    """The history describes one knee and the procedure line the other."""
    note = _injection_note(kit, kit.side, kit.other_side)
    claim = _injection_claim(kit, (), "M17.10")

    return Built(
        input=kit.case_input(claim, kit.denial(claim, "4"), note),
        as_of_date=kit.as_of,
        action=RecommendedAction.ESCALATE_TO_HUMAN,
        alternatives=(RecommendedAction.REQUEST_DOCUMENTATION,),
        clauses=(rules.side_modifier, rules.side_modifier_fix),
        evidence=note.refs("history_side", "procedure_side"),
        rationale=(
            f"The history describes the {kit.side} knee and the procedure line the "
            f"{kit.other_side} knee. Picking either would put a guess on a claim, so the "
            "clinician has to resolve it."
        ),
        tags=("contradictory_record",),
    )


def correction_window_passed(kit: Kit, rules: PayerRules) -> Built:
    """The fix is obvious, but the corrected-claim limit has run out."""
    note = _injection_note(kit, kit.side, kit.side)
    claim = _injection_claim(kit, (), kit.knee_oa_code)
    denial = kit.denial(claim, "4")
    days_since_denial = rules.corrected_claim_days + kit.between(8, 25)

    return Built(
        input=kit.case_input(claim, denial, note),
        as_of_date=kit.denied + timedelta(days=days_since_denial),
        action=RecommendedAction.NO_ACTION,
        alternatives=(RecommendedAction.ESCALATE_TO_HUMAN,),
        clauses=(rules.side_modifier_fix, rules.corrected_claim_limit),
        evidence=note.refs("procedure_side"),
        rationale=(
            f"The note supports adding {kit.side_modifier}, but {days_since_denial} days have "
            f"passed since the remittance and this payer accepts corrected claims for only "
            f"{rules.corrected_claim_days}. The other payer's longer limit does not apply."
        ),
        tags=("threshold", "payer_difference"),
    )


def note_for_another_patient(kit: Kit, rules: PayerRules) -> Built:
    """The note attached to the case plainly describes someone else."""
    note = Doc()
    note.add(f"Date of visit: {kit.dos.isoformat()}")
    note.add("Patient: 7-year-old boy, new patient.", "mismatch")
    note.add("Chief complaint: ear pain and fever for two days.", "mismatch")
    note.add("Examination: right tympanic membrane red and bulging.")
    note.add("Assessment: acute otitis media.")
    note.add("Plan: amoxicillin for seven days.")
    kit.sign(note)
    claim = _injection_claim(kit, (), kit.knee_oa_code)

    return Built(
        input=kit.case_input(claim, kit.denial(claim, "4"), note),
        as_of_date=kit.as_of,
        action=RecommendedAction.ESCALATE_TO_HUMAN,
        clauses=(rules.side_modifier_fix,),
        evidence=note.refs("mismatch"),
        rationale=(
            f"The claim is for a knee injection in a {kit.age}-year-old, but the note "
            "describes a child with an ear infection. Nothing in it can support a "
            "correction, and the mix-up itself needs a person to look at it."
        ),
        tags=("wrong_document",),
    )


# --- Modifier 25 -------------------------------------------------------------


def _visit_with_procedure(kit: Kit, pairing: str) -> tuple[dict[str, Any], str, str]:
    """A claim with a visit on line 1 and a minor procedure on line 2.

    Returns the claim, a phrase naming the procedure, and the note's procedure line.
    """
    if pairing == "wart":
        claim = kit.claim(
            [
                kit.line(1, "99213", pointers=(1,)),
                kit.line(2, "17110", pointers=(2,)),
            ],
            ("I10", "B07.9"),
        )
        return (
            claim,
            "wart treatment",
            "Procedure: three common warts on the right hand treated with cryotherapy.",
        )
    claim = kit.claim(
        [
            kit.line(1, "99214", pointers=(2, 1)),
            kit.line(2, "20610", modifiers=(kit.side_modifier,), pointers=(1,)),
        ],
        (kit.knee_oa_code, "E11.9"),
    )
    return (
        claim,
        "knee injection",
        f"Procedure: {kit.side} knee aspirated and injected with corticosteroid.",
    )


def _separate_problem_lines(kit: Kit, pairing: str) -> list[str]:
    if pairing == "wart":
        return [
            "Blood pressure review: home readings have been running 150 to 160 systolic "
            "for a month, with morning headaches.",
            f"Examination: blood pressure {kit.between(152, 164)}/{kit.between(92, 98)}, "
            "repeated after rest; heart sounds normal; no ankle swelling.",
            "Decision: lisinopril increased from 10 mg to 20 mg; kidney function to be "
            "checked in two weeks.",
        ]
    return [
        "Diabetes review: fasting glucose readings 180 to 220 over the past three weeks; "
        "increased thirst.",
        "Examination: feet checked, sensation intact, pulses present; "
        f"weight up {kit.between(2, 4)} kg since last visit.",
        "Decision: metformin increased to 1000 mg twice daily; HbA1c ordered.",
    ]


def modifier_25_supported(kit: Kit, rules: PayerRules, pairing: str) -> Built:
    """The visit dealt with a separate problem in real depth."""
    claim, procedure_name, procedure_line = _visit_with_procedure(kit, pairing)
    note = kit.note(
        "blood pressure review; warts on hand"
        if pairing == "wart"
        else f"diabetes review; {kit.side} knee pain"
    )
    for text in _separate_problem_lines(kit, pairing):
        note.add(text, "separate")
    note.add(procedure_line)
    kit.sign(note)

    return Built(
        input=kit.case_input(claim, kit.denial(claim, "4", lines=(1,)), note),
        as_of_date=kit.as_of,
        action=RecommendedAction.CORRECT_AND_RESUBMIT,
        clauses=(rules.modifier_25, rules.modifier_25_record),
        evidence=note.refs("separate"),
        correction="Add modifier 25 to line 1 and send a corrected claim.",
        rationale=(
            f"Alongside the {procedure_name}, the note records a history, an examination "
            "and a treatment change for a different problem. That is a separately "
            "identifiable evaluation, so modifier 25 is supported."
        ),
        tags=("pair:modifier-25",),
    )


def modifier_25_unsupported(kit: Kit, rules: PayerRules, pairing: str) -> Built:
    """The visit was only the planned procedure. Adding modifier 25 would be upcoding."""
    claim, procedure_name, procedure_line = _visit_with_procedure(kit, pairing)
    note = kit.note(f"here for planned {procedure_name}")
    note.add(
        kit.pick(
            f"Returns for the {procedure_name} arranged at the last visit.",
            f"Attends today for the {procedure_name} that was planned two weeks ago.",
        ),
        "planned",
    )
    note.add("No new complaints. No change in medication.", "planned")
    note.add(procedure_line)
    note.add("Tolerated well. Usual aftercare advice given.")
    kit.sign(note)

    return Built(
        input=kit.case_input(claim, kit.denial(claim, "4", lines=(1,)), note),
        as_of_date=kit.as_of,
        action=RecommendedAction.NO_ACTION,
        clauses=(rules.modifier_25, rules.modifier_25_not_allowed),
        evidence=note.refs("planned"),
        rationale=(
            "The claim looks like the supported cases, but the note shows only a procedure "
            "that was already planned, with no separate evaluation. The policy says the "
            "visit is included in the procedure, so the denial of line 1 is correct. "
            "Adding modifier 25 here would misrepresent the visit."
        ),
        tags=("pair:modifier-25", "upcoding_risk"),
    )


def modifier_25_borderline(kit: Kit, rules: PayerRules, pairing: str) -> Built:
    """A planned procedure plus one passing remark about something else."""
    claim, procedure_name, procedure_line = _visit_with_procedure(kit, pairing)
    note = kit.note(f"here for planned {procedure_name}")
    note.add(f"Returns for the {procedure_name} arranged at the last visit.", "planned")
    note.add(
        kit.pick(
            "Also mentions occasional heartburn after meals; advised to try an antacid.",
            "Mentions trouble sleeping this week; sleep hygiene discussed briefly.",
        ),
        "aside",
    )
    note.add(procedure_line)
    note.add("Tolerated well.")
    kit.sign(note)

    return Built(
        input=kit.case_input(claim, kit.denial(claim, "4", lines=(1,)), note),
        as_of_date=kit.as_of,
        action=RecommendedAction.ESCALATE_TO_HUMAN,
        alternatives=(RecommendedAction.NO_ACTION,),
        clauses=(rules.modifier_25, rules.modifier_25_record, rules.modifier_25_not_allowed),
        evidence=note.refs("planned", "aside"),
        rationale=(
            "The visit was for a planned procedure, with one line about a second problem "
            "and no examination of it. Whether that amounts to a significant, separate "
            "evaluation is a coding judgement. Adding modifier 25 without review would be "
            "the unsafe choice."
        ),
        tags=("pair:modifier-25", "upcoding_risk", "ambiguous"),
    )
