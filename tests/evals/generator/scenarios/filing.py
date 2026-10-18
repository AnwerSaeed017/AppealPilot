"""Denials for late filing (reason code 29)."""

from datetime import date, timedelta
from typing import Any

from app.schemas.recommended_action import RecommendedAction
from tests.evals.generator.clinical import office_visit
from tests.evals.generator.kit import Built, Doc, Kit
from tests.evals.generator.payer_rules import PayerRules


def _visit_claim(kit: Kit) -> tuple[dict[str, Any], Doc]:
    service = office_visit(kit)
    claim = kit.claim([kit.line(1, service.code)], service.diagnoses)
    return claim, service.write_note(kit)


def limit_exceeded(kit: Kit, rules: PayerRules, days_late: tuple[int, int]) -> Built:
    """Filed late, with no exception and no proof of an earlier filing."""
    days_to_submission = rules.filing_limit_days + kit.between(*days_late)
    kit.reschedule(submit_after=days_to_submission)
    claim, note = _visit_claim(kit)
    billing = Doc("BILL")
    billing.add(f"Billing note, {kit.as_of.isoformat()}")
    billing.add(f"First submission of this claim: {kit.submitted.isoformat()}.", "first")
    billing.add(
        kit.pick(
            "The claim sat in a work queue after a staffing change.",
            "The charge was entered late after a coding backlog.",
        ),
        "first",
    )
    billing.add("The patient has no other insurance on file.")

    return Built(
        input=kit.case_input(
            claim, kit.denial(claim, "29"), note, documents=((billing, "BILLING_NOTE", kit.as_of),)
        ),
        as_of_date=kit.as_of,
        action=RecommendedAction.NO_ACTION,
        clauses=(rules.filing_limit, rules.filing_final),
        evidence=billing.refs("first"),
        rationale=(
            f"The claim was first submitted {days_to_submission} days after the service and "
            f"this payer's limit is {rules.filing_limit_days}. The delay was the practice's "
            "own, no listed exception applies, and there is no earlier filing to prove."
        ),
        tags=("threshold", "payer_difference"),
    )


def accepted_on_time(kit: Kit, rules: PayerRules) -> Built:
    """The payer accepted the original filing on time, and a clearinghouse report shows it."""
    first_accepted = kit.dos + timedelta(days=kit.between(8, 30))
    kit.reschedule(submit_after=rules.filing_limit_days + kit.between(20, 45))
    claim, note = _visit_claim(kit)
    report = Doc("CLR")
    report.add("Clearinghouse claim status report")
    report.add(f"Claim: {kit.claim_id}")
    report.add(f"Accepted by payer ({rules.name}): {first_accepted.isoformat()}", "accepted")
    report.add("Status: Accepted", "accepted")

    return Built(
        input=kit.case_input(
            claim,
            kit.denial(claim, "29"),
            note,
            documents=((report, "CLEARINGHOUSE_REPORT", first_accepted),),
        ),
        as_of_date=kit.as_of,
        action=RecommendedAction.APPEAL_WITH_EVIDENCE,
        clauses=(rules.filing_limit, rules.filing_proof),
        evidence=report.refs("accepted"),
        rationale=(
            "The submission on the claim record is a later resend. The clearinghouse report "
            f"shows the payer accepted the claim {(first_accepted - kit.dos).days} days after "
            "the service, inside the limit, and that report is the proof the policy names."
        ),
    )


def sent_but_not_shown_accepted(kit: Kit, rules: PayerRules) -> Built:
    """The practice's own system says "sent", which the policy does not accept as proof."""
    first_sent = kit.dos + timedelta(days=kit.between(8, 30))
    kit.reschedule(submit_after=rules.filing_limit_days + kit.between(20, 45))
    claim, note = _visit_claim(kit)
    history = Doc("BILL")
    history.add("Billing system claim history (screen print)")
    history.add(f"Claim: {kit.claim_id}")
    history.add(f"Sent: {first_sent.isoformat()}", "sent")
    history.add("Status: Sent", "sent")
    history.add("No payer acknowledgement on file.", "sent")

    return Built(
        input=kit.case_input(
            claim,
            kit.denial(claim, "29"),
            note,
            documents=((history, "BILLING_NOTE", kit.as_of),),
        ),
        as_of_date=kit.as_of,
        action=RecommendedAction.REQUEST_DOCUMENTATION,
        clauses=(rules.filing_proof,),
        evidence=history.refs("sent"),
        missing=(
            "clearinghouse or plan acceptance report showing the claim was accepted "
            "within the filing limit",
        ),
        rationale=(
            "The billing system shows the claim was sent on time, but the policy accepts "
            "only a report that the payer accepted it. The screen print cannot carry an "
            "appeal; the clearinghouse report has to be obtained first."
        ),
    )


def primary_payer_first(kit: Kit, rules: PayerRules) -> Built:
    """Another payer was primary, and the claim followed its explanation of benefits in time."""
    kit.reschedule(submit_after=rules.filing_limit_days + kit.between(30, 60))
    days_after_eob = kit.between(10, rules.primary_eob_days - 10)
    statement_date = kit.submitted - timedelta(days=days_after_eob)
    claim, note = _visit_claim(kit)
    eob = Doc("EOB")
    eob.add("Explanation of benefits from the primary payer")
    eob.add(f"Statement date: {statement_date.isoformat()}", "statement")
    eob.add(f"Patient account: {kit.patient_id}")
    eob.add(f"Date of service: {kit.dos.isoformat()}", "statement")
    eob.add("Primary payment made; remaining balance forwarded to the secondary payer.")

    return Built(
        input=kit.case_input(
            claim,
            kit.denial(claim, "29"),
            note,
            documents=((eob, "PRIMARY_PAYER_EOB", statement_date),),
        ),
        as_of_date=kit.as_of,
        action=RecommendedAction.APPEAL_WITH_EVIDENCE,
        clauses=(rules.filing_exceptions, rules.filing_limit),
        evidence=eob.refs("statement"),
        rationale=(
            f"The claim missed the ordinary limit, but it was received {days_after_eob} days "
            "after the primary payer's explanation of benefits, and this payer allows "
            f"{rules.primary_eob_days} days from that date."
        ),
        tags=("threshold",),
    )


def earlier_limit_applies(kit: Kit, rules: PayerRules) -> Built:
    """Tessaly's old 365-day limit still covers services before 2026."""
    days_to_submission = kit.between(200, 300)
    kit.reschedule(
        dos=date(2025, kit.between(9, 11), kit.between(1, 28)), submit_after=days_to_submission
    )
    claim, note = _visit_claim(kit)

    return Built(
        input=kit.case_input(claim, kit.denial(claim, "29"), note),
        as_of_date=kit.as_of,
        action=RecommendedAction.APPEAL_WITH_EVIDENCE,
        clauses=("TESS-TF-1.2",),
        rationale=(
            f"The service was in 2025, so the 365-day limit applies, not the 180-day one. "
            f"The claim was received {days_to_submission} days after the service, which is "
            "on time. The dates on the claim are the evidence."
        ),
        tags=("effective_date",),
    )
