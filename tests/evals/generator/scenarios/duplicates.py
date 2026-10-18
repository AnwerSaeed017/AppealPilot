"""Denials as a duplicate (reason code 18)."""

import copy

from app.schemas.recommended_action import RecommendedAction
from tests.evals.generator.clinical import joint_injection, office_visit
from tests.evals.generator.kit import Built, Kit
from tests.evals.generator.payer_rules import PayerRules


def _leave_room_for_prior_claim(kit: Kit) -> None:
    """Submit late enough that an earlier claim fits between the service and this one."""
    kit.reschedule(submit_after=kit.between(30, 45))


def already_paid(kit: Kit, rules: PayerRules) -> Built:
    """The same line was paid on an earlier claim."""
    _leave_room_for_prior_claim(kit)
    service = office_visit(kit)
    line = kit.line(1, service.code)
    claim = kit.claim([line], service.diagnoses)
    paid = kit.prior_claim([copy.deepcopy(line)], outcome="PAID")

    return Built(
        input=kit.case_input(
            claim, kit.denial(claim, "18"), service.write_note(kit), prior_claims=(paid,)
        ),
        as_of_date=kit.as_of,
        action=RecommendedAction.NO_ACTION,
        clauses=(rules.duplicate_definition, rules.duplicate_paid),
        rationale=(
            f"Prior claim {paid['claim_id']} has the same date of service, procedure, "
            "modifiers and units, and it was paid. The duplicate denial is correct and "
            "sending the claim again would only repeat it."
        ),
    )


def changed_claim_sent_as_new(kit: Kit, rules: PayerRules) -> Built:
    """A fixed claim went in as a new claim instead of a replacement."""
    _leave_room_for_prior_claim(kit)
    service = joint_injection(kit)
    original_line = kit.line(1, service.code)
    original = kit.prior_claim([original_line], outcome="DENIED", carc="4")
    claim = kit.claim([kit.line(1, service.code, modifiers=service.modifiers)], service.diagnoses)
    note = service.write_note(kit)

    return Built(
        input=kit.case_input(claim, kit.denial(claim, "18"), note, prior_claims=(original,)),
        as_of_date=kit.as_of,
        action=RecommendedAction.CORRECT_AND_RESUBMIT,
        clauses=(rules.duplicate_replacement,),
        evidence=note.refs("service"),
        correction=(
            f"Send the claim again as a replacement that references original claim "
            f"{original['claim_id']}."
        ),
        rationale=(
            "The earlier claim was denied for a missing side modifier. The practice added "
            "the modifier but sent the result as a new claim, which the payer treats as a "
            "duplicate. The content is right; it has to go in as a replacement."
        ),
    )


def repeated_service(kit: Kit, rules: PayerRules) -> Built:
    """Two ECGs on the same day, both documented, billed without a repeat modifier."""
    note = kit.note("palpitations")
    note.add("History: two episodes of palpitations this morning.")
    note.add("09:10 ECG: sinus rhythm, rate 78, no acute changes.", "first")
    note.add("10:40 Palpitations returned while waiting; patient light-headed.", "second")
    note.add("10:45 Repeat ECG: narrow-complex tachycardia, rate 164.", "second")
    note.add("Plan: vagal manoeuvres effective; cardiology referral.")
    kit.sign(note)
    claim = kit.claim([kit.line(1, "93000"), kit.line(2, "93000")], ("R00.2",))

    return Built(
        input=kit.case_input(claim, kit.denial(claim, "18", lines=(2,)), note),
        as_of_date=kit.as_of,
        action=RecommendedAction.CORRECT_AND_RESUBMIT,
        clauses=(rules.duplicate_repeat,),
        evidence=note.refs("first", "second"),
        correction="Add modifier 76 to line 2 and send a corrected claim.",
        rationale=(
            "The note records two ECGs at different times with different findings, so the "
            "second is a repeat and not a duplicate. The policy asks for modifier 76 on "
            "the repeat line, which is all that is missing."
        ),
    )


def duplicate_of_unexplained_denial(kit: Kit, rules: PayerRules) -> Built:
    """The earlier claim was denied too, and nobody recorded why."""
    _leave_room_for_prior_claim(kit)
    service = joint_injection(kit)
    line = kit.line(1, service.code, modifiers=service.modifiers)
    earlier = kit.prior_claim([copy.deepcopy(line)], outcome="DENIED")
    claim = kit.claim([line], service.diagnoses)

    return Built(
        input=kit.case_input(
            claim, kit.denial(claim, "18"), service.write_note(kit), prior_claims=(earlier,)
        ),
        as_of_date=kit.as_of,
        action=RecommendedAction.ESCALATE_TO_HUMAN,
        alternatives=(RecommendedAction.REQUEST_DOCUMENTATION,),
        clauses=("TESS-DUP-3.1",),
        rationale=(
            "The policy says a duplicate of a denied line is settled by the reason for the "
            f"earlier denial, but prior claim {earlier['claim_id']} has no reason on file. "
            "Without it there is no basis for choosing a correction, an appeal or nothing."
        ),
        tags=("missing_history",),
    )
