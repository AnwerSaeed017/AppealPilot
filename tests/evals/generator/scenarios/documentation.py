"""Denials pending documentation (reason code 252)."""

from datetime import timedelta

from app.schemas.recommended_action import RecommendedAction
from tests.evals.generator.kit import Built, Doc, Kit
from tests.evals.generator.payer_rules import PayerRules


def hyaluronan(kit: Kit, rules: PayerRules, months_of_treatment: int | None) -> Built:
    """Hyaluronan injection, where the two payers ask for different lengths of treatment.

    `months_of_treatment` of None writes a note that mentions treatment without dates.
    """
    note = kit.note(f"{kit.side} knee pain from osteoarthritis")
    note.add(
        f"Radiograph of the {kit.side} knee, {(kit.dos - timedelta(days=200)).isoformat()}: "
        "joint-space narrowing and osteophytes, consistent with osteoarthritis.",
        "radiograph",
    )
    if months_of_treatment is None:
        note.add(
            "Has tried anti-inflammatory tablets and physiotherapy in the past "
            "without lasting benefit.",
            "undated",
        )
    else:
        started = kit.dos - timedelta(days=months_of_treatment * 30 + kit.between(3, 12))
        therapy_from = started + timedelta(days=14)
        therapy_to = therapy_from + timedelta(days=56)
        note.add(
            f"Naproxen 500 mg twice daily started {started.isoformat()}; still taking it "
            "with little relief.",
            "treatment",
        )
        note.add(
            f"Supervised physical therapy: {kit.between(8, 12)} sessions from "
            f"{therapy_from.isoformat()} to {therapy_to.isoformat()}; pain unchanged.",
            "treatment",
        )
    note.add("Examination: crepitus, small effusion, flexion limited to 100 degrees.")
    note.add(f"Procedure: hyaluronan injected into the {kit.side} knee.")
    kit.sign(note)

    claim = kit.claim(
        [kit.line(1, "J7325", modifiers=(kit.side_modifier,))],
        (kit.knee_oa_code,),
        authorization=kit.reference("AU"),
    )
    denial = kit.denial(claim, "252", remark="Records of conservative treatment are required.")
    case_input = kit.case_input(claim, denial, note)

    if months_of_treatment is None:
        return Built(
            input=case_input,
            as_of_date=kit.as_of,
            action=RecommendedAction.REQUEST_DOCUMENTATION,
            clauses=(rules.hyaluronan,),
            evidence=note.refs("radiograph", "undated"),
            missing=(
                "start date and duration of analgesic treatment",
                "physical therapy records with session dates",
            ),
            rationale=(
                "The radiograph requirement is met, but the note says only that treatment "
                "was tried 'in the past'. The policy sets a minimum duration, and no "
                "duration can be stated from this note without inventing it."
            ),
        )
    if months_of_treatment >= rules.hyaluronan_months:
        return Built(
            input=case_input,
            as_of_date=kit.as_of,
            action=RecommendedAction.APPEAL_WITH_EVIDENCE,
            clauses=(rules.hyaluronan, rules.documentation_deadline),
            evidence=note.refs("radiograph", "treatment"),
            rationale=(
                "The note has a confirming radiograph, and dated analgesic treatment and "
                f"physical therapy running about {months_of_treatment} months before the "
                f"injection. This payer requires {rules.hyaluronan_months} months, so the "
                "requested records exist and meet the clause."
            ),
            tags=("threshold", "payer_difference"),
        )
    return Built(
        input=case_input,
        as_of_date=kit.as_of,
        action=RecommendedAction.NO_ACTION,
        alternatives=(RecommendedAction.ESCALATE_TO_HUMAN,),
        clauses=(rules.hyaluronan, rules.documentation_absent),
        evidence=note.refs("treatment"),
        rationale=(
            f"The record is complete and shows about {months_of_treatment} months of "
            f"treatment, but this payer requires {rules.hyaluronan_months}. Sending the "
            "records would document that the requirement was not met. The same record "
            "would satisfy the other payer."
        ),
        tags=("threshold", "payer_difference"),
    )


def positive_airway_pressure(kit: Kit, rules: PayerRules, report_on_file: bool) -> Built:
    """A CPAP device, which needs a sleep study report with the measured index."""
    study_date = kit.dos - timedelta(days=kit.between(14, 35))
    evaluation_date = study_date - timedelta(days=kit.between(10, 25))
    index = kit.between(17, 34)
    note = kit.note("follow-up after sleep study")
    note.add(
        f"Initial evaluation {evaluation_date.isoformat()}: loud snoring, witnessed pauses "
        "in breathing, daytime sleepiness.",
        "evaluation",
    )
    note.add(
        f"Sleep study {study_date.isoformat()}: positive for obstructive sleep apnea.", "study"
    )
    note.add("Plan: start positive airway pressure therapy; device ordered today.")
    kit.sign(note)

    claim = kit.claim([kit.line(1, "E0601")], ("G47.33",))
    denial = kit.denial(claim, "252", remark="Sleep study report is required.")

    if not report_on_file:
        return Built(
            input=kit.case_input(claim, denial, note),
            as_of_date=kit.as_of,
            action=RecommendedAction.REQUEST_DOCUMENTATION,
            clauses=(rules.cpap,),
            evidence=note.refs("study"),
            missing=("sleep study report showing the apnea-hypopnea index",),
            rationale=(
                "The note says the study was positive but gives no index, and the policy "
                "turns on the number. The report itself is not in the file and has to be "
                "obtained from the sleep laboratory."
            ),
        )

    report = Doc("SLEEP")
    report.add("Attended polysomnography report")
    report.add(f"Study date: {study_date.isoformat()}")
    report.add(f"Apnea-hypopnea index (AHI): {index} events per hour", "index")
    report.add("Impression: obstructive sleep apnea.")
    return Built(
        input=kit.case_input(
            claim, denial, note, documents=((report, "DIAGNOSTIC_REPORT", study_date),)
        ),
        as_of_date=kit.as_of,
        action=RecommendedAction.APPEAL_WITH_EVIDENCE,
        clauses=(rules.cpap, rules.documentation_deadline),
        evidence=report.refs("index") + note.refs("evaluation"),
        rationale=(
            f"The report on file gives an index of {index}, above the threshold of 15, and "
            "the note records a clinical evaluation before the study. The documentation "
            "the payer asked for exists and can be sent within the deadline."
        ),
    )


def therapy_without_progress_note(kit: Kit, rules: PayerRules) -> Built:
    """Extended physical therapy with a plan of care but no measured progress."""
    visit_number = kit.between(13, 16)
    note = kit.note("low back pain, physical therapy session")
    note.add(f"Physical therapy visit {visit_number} of this calendar year.", "visit_count")
    note.add("Session: therapeutic exercise, 30 minutes: core stabilisation and stretches.")
    note.add("Patient reports feeling stronger and wishes to continue.", "subjective")
    kit.sign(note)

    plan_date = kit.dos - timedelta(days=kit.between(35, 50))
    plan = Doc("POC")
    plan.add("Physical therapy plan of care")
    plan.add(f"Written: {plan_date.isoformat()}")
    plan.add("Goal 1: lumbar flexion from 40 to 60 degrees within 8 weeks.", "goals")
    plan.add("Goal 2: sit for 45 minutes without pain within 8 weeks.", "goals")

    claim = kit.claim([kit.line(1, "97110", units=2)], ("M54.50",))
    denial = kit.denial(
        claim, "252", remark="Plan of care and progress note are required for extended therapy."
    )

    return Built(
        input=kit.case_input(claim, denial, note, documents=((plan, "PLAN_OF_CARE", plan_date),)),
        as_of_date=kit.as_of,
        action=RecommendedAction.REQUEST_DOCUMENTATION,
        clauses=("TESS-DOC-2.3",),
        evidence=note.refs("visit_count", "subjective") + plan.refs("goals"),
        missing=("progress note with objective measurements since the plan of care was written",),
        rationale=(
            f"Visit {visit_number} is past the 12-visit threshold. The plan of care with "
            "measurable goals exists, but the only sign of progress is the patient's own "
            "report, and the policy asks for objective improvement."
        ),
    )
