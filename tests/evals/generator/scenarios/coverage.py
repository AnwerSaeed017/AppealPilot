"""Denials about the diagnosis (reason code 11) and medical necessity (reason code 50)."""

from datetime import timedelta
from typing import Any

from app.schemas.recommended_action import RecommendedAction
from tests.evals.generator.kit import Built, Doc, Kit
from tests.evals.generator.payer_rules import PayerRules

# --- Diagnosis does not support the procedure (11) ----------------------------


# A long-term condition that is on the claim but has nothing to do with the knee:
# diagnosis code, the note's line about it, and how the rationale names it.
_OTHER_CONDITIONS: dict[str, tuple[str, str, str]] = {
    "diabetes": ("E11.9", "Type 2 diabetes: stable on metformin, no changes today.", "diabetes"),
    "hypertension": (
        "I10",
        "Hypertension: well controlled on amlodipine, no changes today.",
        "hypertension",
    ),
}


def _injection_note(kit: Kit, other_condition_line: str) -> Doc:
    note = kit.note(f"{kit.side} knee pain")
    note.add(f"History: osteoarthritis of the {kit.side} knee, pain worse over two months.", "knee")
    note.add(other_condition_line)
    note.add("Examination: crepitus and a small effusion.", "knee")
    note.add(
        f"Assessment: primary osteoarthritis, {kit.side} knee, with effusion.",
        "knee",
    )
    note.add(f"Procedure: {kit.side} knee aspirated and injected with corticosteroid.")
    return kit.sign(note)


def diagnosis_pointer_wrong(
    kit: Kit, rules: PayerRules, other_condition: str = "diabetes"
) -> Built:
    """The right diagnosis is on the claim, but the line points at another condition."""
    other_code, other_line, other_name = _OTHER_CONDITIONS[other_condition]
    note = _injection_note(kit, other_line)
    claim = kit.claim(
        [kit.line(1, "20610", modifiers=(kit.side_modifier,), pointers=(1,))],
        (other_code, kit.knee_oa_code),
    )

    return Built(
        input=kit.case_input(claim, kit.denial(claim, "11"), note),
        as_of_date=kit.as_of,
        action=RecommendedAction.CORRECT_AND_RESUBMIT,
        clauses=(rules.diagnosis_support, rules.diagnosis_fix, rules.joint_injection),
        evidence=note.refs("knee"),
        correction=(
            f"Change the diagnosis pointer on line 1 so that {kit.knee_oa_code} is the "
            "first diagnosis, and send a corrected claim."
        ),
        rationale=(
            f"The injection line points only at {other_name}, which does not support a joint "
            "injection. The note for the same date documents knee osteoarthritis with an "
            "effusion, and that diagnosis is already on the claim, so the pointer is wrong."
        ),
    )


def diagnosis_denial_wrong(kit: Kit, rules: PayerRules) -> Built:
    """The line already points at a supporting diagnosis; the denial is mistaken."""
    other_code, other_line, _ = _OTHER_CONDITIONS["diabetes"]
    note = _injection_note(kit, other_line)
    claim = kit.claim(
        [kit.line(1, "20610", modifiers=(kit.side_modifier,), pointers=(1,))],
        (kit.knee_oa_code, other_code),
    )

    return Built(
        input=kit.case_input(claim, kit.denial(claim, "11"), note),
        as_of_date=kit.as_of,
        action=RecommendedAction.APPEAL_WITH_EVIDENCE,
        clauses=(rules.diagnosis_support, rules.joint_injection),
        evidence=note.refs("knee"),
        rationale=(
            f"The first diagnosis on the line is {kit.knee_oa_code}, osteoarthritis of the "
            "knee treated, which the policy lists as supporting the injection, and the note "
            "confirms it. There is nothing to correct, so this is an appeal."
        ),
    )


# --- Medical necessity (50) ---------------------------------------------------


def _knee_mri_claim(kit: Kit, rules: PayerRules) -> dict[str, Any]:
    # Tessaly requires authorization for a knee MRI; Quillon does not.
    authorization = kit.reference("AU") if rules.pa_services.startswith("TESS") else None
    return kit.claim(
        [kit.line(1, "73721", modifiers=(kit.side_modifier,))],
        (kit.knee_pain_code,),
        authorization=authorization,
    )


def knee_mri_with_findings(kit: Kit, rules: PayerRules) -> Built:
    """The examination findings the policy names are written in the note."""
    note = kit.note(f"{kit.side} knee pain after an injury")
    note.add(
        f"History: twisted the {kit.side} knee {kit.between(6, 12)} days ago; "
        + kit.pick("it has locked twice since.", "it has given way on the stairs and locked once."),
        "findings",
    )
    note.add(
        kit.pick(
            "Examination: tender along the medial joint line; McMurray test positive.",
            "Examination: medial joint-line tenderness with a positive McMurray test; "
            "ligaments stable.",
        ),
        "findings",
    )
    note.add("Assessment: suspected medial meniscal tear.")
    note.add(f"Plan: MRI of the {kit.side} knee without contrast.")
    kit.sign(note)
    claim = _knee_mri_claim(kit, rules)

    return Built(
        input=kit.case_input(claim, kit.denial(claim, "50"), note),
        as_of_date=kit.as_of,
        action=RecommendedAction.APPEAL_WITH_EVIDENCE,
        alternatives=(RecommendedAction.ESCALATE_TO_HUMAN,),
        clauses=(rules.knee_mri, rules.necessity_appeal),
        evidence=note.refs("findings"),
        rationale=(
            "The policy supports a knee MRI for a suspected meniscal tear with a positive "
            "examination finding. The note records locking, joint-line tenderness and a "
            "positive McMurray test, so the criterion is met without relying on duration."
        ),
    )


def knee_mri_undated_treatment(kit: Kit, rules: PayerRules) -> Built:
    """The note claims failed conservative treatment but gives no duration."""
    note = kit.note(f"{kit.side} knee pain")
    note.add(
        kit.pick(
            "History: longstanding knee pain. Has failed conservative management.",
            "History: knee pain for some time; conservative measures have not helped.",
        ),
        "undated",
    )
    note.add("Examination: mild medial tenderness; full range of movement; ligaments stable.")
    note.add("Assessment: knee pain, cause unclear.")
    note.add(f"Plan: MRI of the {kit.side} knee without contrast.")
    kit.sign(note)
    claim = _knee_mri_claim(kit, rules)

    return Built(
        input=kit.case_input(claim, kit.denial(claim, "50"), note),
        as_of_date=kit.as_of,
        action=RecommendedAction.REQUEST_DOCUMENTATION,
        alternatives=(RecommendedAction.ESCALATE_TO_HUMAN,),
        clauses=(rules.knee_mri,),
        evidence=note.refs("undated"),
        missing=("dates and duration of the conservative treatment already tried",),
        rationale=(
            "No examination finding in the note meets the first criterion, so the case "
            f"rests on at least {rules.knee_mri_weeks} weeks of conservative treatment. "
            "The note asserts failure of treatment without saying what or for how long."
        ),
    )


def knee_mri_osteoarthritis_only(kit: Kit, rules: PayerRules) -> Built:
    """Neither criterion is met, and the note is clear about it."""
    note = kit.note(f"{kit.side} knee pain")
    note.add(
        f"History: known osteoarthritis of the {kit.side} knee; pain for 2 weeks after "
        "gardening. No locking or giving way.",
        "picture",
    )
    note.add(
        "Examination: crepitus; no joint-line tenderness; ligaments stable; "
        "McMurray test negative.",
        "picture",
    )
    note.add("Assessment: flare of osteoarthritis.")
    note.add(f"Plan: MRI of the {kit.side} knee at the patient's request.")
    kit.sign(note)
    claim = _knee_mri_claim(kit, rules)

    return Built(
        input=kit.case_input(claim, kit.denial(claim, "50"), note),
        as_of_date=kit.as_of,
        action=RecommendedAction.NO_ACTION,
        alternatives=(RecommendedAction.ESCALATE_TO_HUMAN,),
        clauses=(rules.knee_mri,),
        evidence=note.refs("picture"),
        rationale=(
            "The note records osteoarthritis, two weeks of pain, a negative McMurray test "
            "and no locking. The policy says osteoarthritis alone does not support the "
            "scan, and no honest appeal can be built from this record."
        ),
    )


def knee_mri_late_addendum(kit: Kit, rules: PayerRules) -> Built:
    """The decisive finding appears only in an addendum written after the denial."""
    note = kit.note(f"{kit.side} knee pain")
    note.add(f"History: {kit.side} knee pain for 3 weeks. No injury recalled.")
    note.add("Examination: mild tenderness. Ligaments stable.", "original")
    note.add("Assessment: knee pain.")
    note.add(f"Plan: MRI of the {kit.side} knee without contrast.")
    kit.sign(note)

    added = kit.denied + timedelta(days=3)
    addendum = Doc("ADD")
    addendum.add(f"Late entry, added {added.isoformat()}.", "late")
    addendum.add(f"At the visit on {kit.dos.isoformat()} the McMurray test was positive.", "late")
    claim = _knee_mri_claim(kit, rules)

    return Built(
        input=kit.case_input(
            claim, kit.denial(claim, "50"), note, documents=((addendum, "ADDENDUM", added),)
        ),
        as_of_date=max(kit.as_of, added),
        action=RecommendedAction.ESCALATE_TO_HUMAN,
        alternatives=(RecommendedAction.NO_ACTION,),
        clauses=(rules.knee_mri, rules.documentation_acceptable),
        evidence=note.refs("original") + addendum.refs("late"),
        rationale=(
            "The original note has no finding that supports the scan. The positive "
            "McMurray test appears only in an addendum written after the denial, and the "
            "policy rejects late entries that add findings. Building an appeal on it is a "
            "compliance question for a person."
        ),
        tags=("late_entry",),
    )


def lumbar_mri_equivocal(kit: Kit, rules: PayerRules) -> Built:
    """Just under the duration threshold, with a finding the clinician hedged."""
    note = kit.note("low back pain")
    note.add(
        "History: low back pain for 5 weeks. Ibuprofen and home exercises for 5 weeks "
        "with partial relief.",
        "duration",
    )
    note.add(
        "Examination: possible mild weakness of ankle dorsiflexion, limited by pain; "
        "reflexes symmetric; sensation intact.",
        "hedged",
    )
    note.add("Assessment: low back pain, possible early nerve root irritation.")
    note.add("Plan: MRI of the lumbar spine without contrast.")
    kit.sign(note)
    claim = kit.claim([kit.line(1, "72148")], ("M54.50",), authorization=kit.reference("AU"))

    return Built(
        input=kit.case_input(claim, kit.denial(claim, "50"), note),
        as_of_date=kit.as_of,
        action=RecommendedAction.ESCALATE_TO_HUMAN,
        alternatives=(RecommendedAction.REQUEST_DOCUMENTATION,),
        clauses=(rules.lumbar_mri, rules.necessity_appeal),
        evidence=note.refs("duration", "hedged"),
        rationale=(
            "Five weeks of treatment is short of the six the policy asks for, so the case "
            "depends on a neurological deficit. The note says 'possible' weakness 'limited "
            "by pain'. Calling that a deficit would overstate the record; whether it is one "
            "is a clinical judgement."
        ),
        tags=("ambiguous", "hedged_finding"),
    )


def cosmetic_removal(kit: Kit, rules: PayerRules) -> Built:
    """Tessaly excludes lesion removal done for appearance."""
    note = kit.note("skin lesions on the back")
    note.add(
        "History: several raised brown lesions on the back for years. Not painful; "
        "no bleeding or itching.",
        "symptoms",
    )
    note.add("The patient dislikes their appearance and asks for removal.", "reason")
    note.add("Examination: six seborrhoeic keratoses, none inflamed.", "symptoms")
    note.add("Procedure: six lesions treated with cryotherapy.")
    kit.sign(note)
    claim = kit.claim([kit.line(1, "17110")], ("L82.1",))

    return Built(
        input=kit.case_input(claim, kit.denial(claim, "50"), note),
        as_of_date=kit.as_of,
        action=RecommendedAction.NO_ACTION,
        clauses=("TESS-COV-3.1",),
        evidence=note.refs("symptoms", "reason"),
        rationale=(
            "The note says the lesions caused no pain, bleeding or inflammation and were "
            "removed because the patient disliked how they looked. The policy excludes "
            "removal for appearance and says the denial is not appealable."
        ),
    )
