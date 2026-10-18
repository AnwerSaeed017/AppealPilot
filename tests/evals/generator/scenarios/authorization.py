"""Denials for absent authorization (reason code 197)."""

from datetime import date, timedelta

from app.schemas.recommended_action import RecommendedAction
from tests.evals.generator.clinical import SERVICES, Service
from tests.evals.generator.kit import Built, Doc, Kit
from tests.evals.generator.payer_rules import PayerRules

_AUTHORIZATION_RECORD = "AUTHORIZATION_RECORD"
_BILLING_NOTE = "BILLING_NOTE"


def _authorization_record(
    kit: Kit, rules: PayerRules, service: Service, number: str, issued: date
) -> Doc:
    record = Doc("AUTH")
    record.add(f"{rules.name}: authorization confirmation")
    record.add(f"Authorization number: {number}", "number")
    record.add(f"Issued: {issued.isoformat()}", "issued")
    record.add(f"Member: {kit.member_id}")
    record.add(f"Service: procedure code {service.code}, {service.label}", "service")
    return record


def _claim_for(kit: Kit, service: Service, authorization: str | None = None) -> dict[str, object]:
    line = kit.line(1, service.code, modifiers=service.modifiers)
    return kit.claim([line], service.diagnoses, authorization=authorization)


def number_omitted(
    kit: Kit, rules: PayerRules, service_key: str, issued_days_before: int | None = None
) -> Built:
    """A valid authorization exists; its number was simply left off the claim."""
    service = SERVICES[service_key](kit)
    number = kit.reference("AU")
    days_before = issued_days_before if issued_days_before is not None else kit.between(5, 30)
    issued = kit.dos - timedelta(days=days_before)
    record = _authorization_record(kit, rules, service, number, issued)
    claim = _claim_for(kit, service)

    return Built(
        input=kit.case_input(
            claim,
            kit.denial(claim, "197"),
            service.write_note(kit),
            documents=((record, _AUTHORIZATION_RECORD, issued),),
        ),
        as_of_date=kit.as_of,
        action=RecommendedAction.CORRECT_AND_RESUBMIT,
        clauses=(rules.pa_number_required, rules.pa_validity, rules.pa_number_omitted),
        evidence=record.refs("number", "issued", "service"),
        correction=f"Add authorization number {number} to the claim and send a corrected claim.",
        rationale=(
            f"The authorization was issued {days_before} days before the service, inside the "
            f"{rules.pa_validity_days}-day validity period, for the procedure billed. Only the "
            "number is missing from the claim, which the policy treats as a correction."
        ),
        tags=("threshold",) if issued_days_before is not None else (),
    )


def on_claim_but_no_record(kit: Kit, rules: PayerRules, service_key: str) -> Built:
    """The claim carried the number and the practice holds the confirmation."""
    service = SERVICES[service_key](kit)
    number = kit.reference("AU")
    issued = kit.dos - timedelta(days=kit.between(5, 30))
    record = _authorization_record(kit, rules, service, number, issued)
    claim = _claim_for(kit, service, authorization=number)

    return Built(
        input=kit.case_input(
            claim,
            kit.denial(claim, "197"),
            service.write_note(kit),
            documents=((record, _AUTHORIZATION_RECORD, issued),),
        ),
        as_of_date=kit.as_of,
        action=RecommendedAction.APPEAL_WITH_EVIDENCE,
        clauses=(rules.pa_appeal, rules.pa_validity),
        evidence=record.refs("number", "issued", "service"),
        rationale=(
            "The claim already carried the authorization number, so there is nothing to "
            "correct. The practice holds the number, the issue date and the service "
            "authorized, which is what the policy requires for an appeal."
        ),
    )


def not_required(kit: Kit, rules: PayerRules, service_key: str) -> Built:
    """The payer's own list says this service needs no authorization."""
    service = SERVICES[service_key](kit)
    note = service.write_note(kit)
    claim = _claim_for(kit, service)

    return Built(
        input=kit.case_input(claim, kit.denial(claim, "197"), note),
        as_of_date=kit.as_of,
        action=RecommendedAction.APPEAL_WITH_EVIDENCE,
        clauses=(rules.pa_services,),
        evidence=note.refs("service"),
        rationale=(
            f"Procedure code {service.code} is named in the policy as a service that does "
            "not require authorization for this payer, so the denial is wrong on its face."
        ),
        tags=("payer_difference",),
    )


def emergency_department(kit: Kit, rules: PayerRules) -> Built:
    """Tessaly waives authorization for services in an emergency department."""
    note = kit.note("sudden severe low back pain with leg weakness")
    note.add("Seen in the emergency department.", "setting")
    note.add(
        "History: pain began this morning; new difficulty passing urine and numbness "
        "around the saddle area."
    )
    note.add("Examination: reduced perineal sensation; weakness in both legs.")
    note.add("Assessment: suspected cauda equina syndrome.")
    note.add("Plan: emergency MRI of the lumbar spine, carried out in the department.", "setting")
    kit.sign(note)
    claim = kit.claim([kit.line(1, "72148")], ("M54.16",), place_of_service="23")

    return Built(
        input=kit.case_input(claim, kit.denial(claim, "197"), note),
        as_of_date=kit.as_of,
        action=RecommendedAction.APPEAL_WITH_EVIDENCE,
        clauses=(rules.pa_urgent,),
        evidence=note.refs("setting"),
        rationale=(
            "The claim's place of service is 23 and the note records that the scan was "
            "done in the emergency department, where the policy requires no authorization."
        ),
    )


def statement_only(kit: Kit, rules: PayerRules, service_key: str) -> Built:
    """Someone says authorization was obtained, but nobody wrote down a reference."""
    service = SERVICES[service_key](kit)
    billing = Doc("BILL")
    billing.add(f"Billing note, {kit.as_of.isoformat()}")
    billing.add(
        kit.pick(
            "Front desk reports that authorization was obtained by telephone before the visit.",
            "Scheduler recalls calling the plan and being told the service was approved.",
        ),
        "statement",
    )
    billing.add("No authorization or call reference number was recorded.", "statement")
    claim = _claim_for(kit, service)

    return Built(
        input=kit.case_input(
            claim,
            kit.denial(claim, "197"),
            service.write_note(kit),
            documents=((billing, _BILLING_NOTE, kit.as_of),),
        ),
        as_of_date=kit.as_of,
        action=RecommendedAction.REQUEST_DOCUMENTATION,
        clauses=(rules.pa_appeal,),
        evidence=billing.refs("statement"),
        missing=(
            "authorization or call reference number",
            "date the authorization was issued",
        ),
        rationale=(
            "The policy says a statement that authorization was obtained is not enough "
            "without a reference number. An appeal now would rest on recollection, so the "
            "reference has to be found first."
        ),
    )


def never_requested(kit: Kit, rules: PayerRules, service_key: str) -> Built:
    """No request was made and the service was not urgent."""
    service = SERVICES[service_key](kit)
    billing = Doc("BILL")
    billing.add(f"Billing note, {kit.as_of.isoformat()}")
    billing.add("No authorization request is on file for this service.", "none")
    billing.add(
        kit.pick(
            "The appointment was booked directly from clinic.",
            "The service was scheduled without going through the authorization desk.",
        )
    )
    claim = _claim_for(kit, service)

    return Built(
        input=kit.case_input(
            claim,
            kit.denial(claim, "197"),
            service.write_note(kit),
            documents=((billing, _BILLING_NOTE, kit.as_of),),
        ),
        as_of_date=kit.as_of,
        action=RecommendedAction.NO_ACTION,
        clauses=(rules.pa_services, rules.pa_none_after_service),
        evidence=billing.refs("none"),
        rationale=(
            "The service is on the payer's authorization list, none was requested, and "
            "nothing in the record suggests it was urgent. The policy says the denial "
            "stands, however reasonable the service was clinically."
        ),
    )


def expired(kit: Kit, rules: PayerRules, service_key: str, issued_days_before: int) -> Built:
    """An authorization exists but had run out by the date of service."""
    service = SERVICES[service_key](kit)
    number = kit.reference("AU")
    issued = kit.dos - timedelta(days=issued_days_before)
    record = _authorization_record(kit, rules, service, number, issued)
    claim = _claim_for(kit, service, authorization=number)

    return Built(
        input=kit.case_input(
            claim,
            kit.denial(
                claim, "197", remark="Authorization on file was not valid on the date of service."
            ),
            service.write_note(kit),
            documents=((record, _AUTHORIZATION_RECORD, issued),),
        ),
        as_of_date=kit.as_of,
        action=RecommendedAction.NO_ACTION,
        clauses=(rules.pa_validity, rules.pa_none_after_service),
        evidence=record.refs("issued"),
        rationale=(
            f"The authorization was issued {issued_days_before} days before the service and "
            f"this payer's authorizations last {rules.pa_validity_days} days, so the service "
            "was not authorized. The same gap would be valid under the other payer's rule."
        ),
        tags=("threshold", "payer_difference"),
    )


def _urgent_lumbar_note(kit: Kit) -> Doc:
    """A lumbar MRI that plainly could not wait; the plan line is tagged "urgency"."""
    note = kit.note("worsening leg weakness with low back pain")
    note.add("History: low back pain for a week; foot drop developing over the last 48 hours.")
    note.add("Examination: ankle dorsiflexion 2/5, clearly weaker than two days ago.")
    note.add("Assessment: progressive motor deficit, lumbar nerve root compression suspected.")
    note.add(
        "Plan: MRI of the lumbar spine this afternoon. Because the weakness is progressing, "
        "imaging could not be delayed.",
        "urgency",
    )
    return kit.sign(note)


def urgent_without_notification(kit: Kit, rules: PayerRules) -> Built:
    """Tessaly accepts urgent services if it was told within two business days."""
    note = _urgent_lumbar_note(kit)
    billing = Doc("BILL")
    billing.add(f"Billing note, {kit.as_of.isoformat()}")
    billing.add("Authorization was not requested before the scan because of the urgency.")
    billing.add("No record found of a notification to the plan after the scan.", "gap")
    claim = kit.claim([kit.line(1, "72148")], ("M54.16",))

    return Built(
        input=kit.case_input(
            claim,
            kit.denial(claim, "197"),
            note,
            documents=((billing, _BILLING_NOTE, kit.as_of),),
        ),
        as_of_date=kit.as_of,
        action=RecommendedAction.REQUEST_DOCUMENTATION,
        alternatives=(RecommendedAction.ESCALATE_TO_HUMAN,),
        clauses=(rules.pa_urgent,),
        evidence=note.refs("urgency") + billing.refs("gap"),
        missing=("record that the plan was notified within 2 business days of the service",),
        rationale=(
            "The note documents why the scan could not wait, which is half of what the "
            "urgent-service clause requires. The other half, notifying the plan within 2 "
            "business days, is not shown either way, so the appeal cannot be written yet."
        ),
    )


def conflicting_clauses(kit: Kit, rules: PayerRules, service_key: str) -> Built:
    """Quillon allows a late request for urgent care, but refuses requests after a claim."""
    service = SERVICES[service_key](kit)
    if service_key == "lumbar_mri":
        # The routine lumbar picture is not urgent, so this one has its own note.
        note = _urgent_lumbar_note(kit)
    else:
        note = kit.note(service.complaint)
        for text, tag in service.lines:
            note.add(text, tag)
        note.add(
            "The procedure was carried out the same day because the knee could not be left locked.",
            "urgency",
        )
        kit.sign(note)

    kit.reschedule(submit_after=kit.between(3, 8))
    requested = kit.dos + timedelta(days=kit.between(10, 13))
    billing = Doc("BILL")
    billing.add(f"Billing note, {kit.as_of.isoformat()}")
    billing.add(f"Claim submitted {kit.submitted.isoformat()}.", "sequence")
    billing.add(
        f"Authorization request for the urgent service sent {requested.isoformat()}, "
        "with the clinic note.",
        "sequence",
    )
    billing.add(
        "The plan declined to accept the request because a claim was already on file.",
        "sequence",
    )
    claim = _claim_for(kit, service)

    return Built(
        input=kit.case_input(
            claim,
            kit.denial(claim, "197"),
            note,
            documents=((billing, _BILLING_NOTE, kit.as_of),),
        ),
        as_of_date=kit.as_of,
        action=RecommendedAction.ESCALATE_TO_HUMAN,
        clauses=(rules.pa_urgent, "QUIL-APL-2.2"),
        evidence=note.refs("urgency") + billing.refs("sequence"),
        rationale=(
            "One clause allows a request within 14 days of an urgent service, and this one "
            "was made in time. Another refuses any request once a claim is on file, and the "
            "claim went in first. The policies do not say which prevails, so a person decides."
        ),
        tags=("conflicting_clauses",),
    )
