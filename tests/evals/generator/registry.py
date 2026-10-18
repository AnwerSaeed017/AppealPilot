"""Every generated case, listed one per line.

Each entry is a scenario applied to one payer and assigned to one split. The key is
part of the seed, so it must stay unique and stable. Counts per action and split are
checked by a test against the plan in docs/appealpilot.md, less the cases that are
written by hand.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.schemas.eval_case import EvalSplit
from tests.evals.generator.kit import Built, Kit
from tests.evals.generator.payer_rules import PayerRules
from tests.evals.generator.scenarios import (
    authorization,
    coverage,
    documentation,
    duplicates,
    filing,
    invalid,
    modifiers,
)

DEV = EvalSplit.DEV
LOCKED = EvalSplit.LOCKED


@dataclass(frozen=True)
class Entry:
    key: str
    split: EvalSplit
    payer: str
    scenario: Callable[..., Built]
    params: dict[str, Any] = field(default_factory=dict)

    def build(self, kit: Kit, rules: PayerRules) -> Built:
        return self.scenario(kit, rules, **self.params)


def _e(
    key: str, split: EvalSplit, payer: str, scenario: Callable[..., Built], **params: Any
) -> Entry:
    return Entry(key, split, payer, scenario, params)


ENTRIES: tuple[Entry, ...] = (
    # --- CORRECT_AND_RESUBMIT: 11 dev, 6 locked ---
    _e("pa-number-omitted-1", DEV, "TESS", authorization.number_omitted, service_key="knee_mri"),
    _e(
        "pa-number-omitted-2",
        DEV,
        "QUIL",
        authorization.number_omitted,
        service_key="lumbar_mri",
        issued_days_before=75,
    ),
    _e(
        "pa-number-omitted-3",
        LOCKED,
        "TESS",
        authorization.number_omitted,
        service_key="sleep_study",
    ),
    _e("side-missing-1", DEV, "TESS", modifiers.side_missing_documented),
    _e("side-missing-2", DEV, "QUIL", modifiers.side_missing_documented),
    _e("side-missing-3", LOCKED, "QUIL", modifiers.side_missing_documented, shorthand=True),
    _e("side-wrong-1", DEV, "TESS", modifiers.side_wrong),
    _e("side-wrong-2", LOCKED, "QUIL", modifiers.side_wrong),
    _e("modifier-25-supported-1", DEV, "TESS", modifiers.modifier_25_supported, pairing="wart"),
    _e("modifier-25-supported-2", DEV, "QUIL", modifiers.modifier_25_supported, pairing="knee"),
    _e("modifier-25-supported-3", LOCKED, "TESS", modifiers.modifier_25_supported, pairing="knee"),
    _e("diagnosis-pointer-1", DEV, "TESS", coverage.diagnosis_pointer_wrong),
    _e("diagnosis-pointer-2", DEV, "QUIL", coverage.diagnosis_pointer_wrong),
    _e(
        "diagnosis-pointer-3",
        LOCKED,
        "QUIL",
        coverage.diagnosis_pointer_wrong,
        other_condition="hypertension",
    ),
    _e("duplicate-sent-as-new-1", DEV, "TESS", duplicates.changed_claim_sent_as_new),
    _e("duplicate-sent-as-new-2", LOCKED, "QUIL", duplicates.changed_claim_sent_as_new),
    _e("duplicate-repeat-1", DEV, "TESS", duplicates.repeated_service),
    # --- APPEAL_WITH_EVIDENCE: 10 dev, 6 locked ---
    _e(
        "pa-no-record-1",
        DEV,
        "TESS",
        authorization.on_claim_but_no_record,
        service_key="lumbar_mri",
    ),
    _e(
        "pa-no-record-2",
        DEV,
        "QUIL",
        authorization.on_claim_but_no_record,
        service_key="hyaluronan",
    ),
    _e(
        "pa-no-record-3",
        LOCKED,
        "QUIL",
        authorization.on_claim_but_no_record,
        service_key="sleep_study",
    ),
    _e("pa-not-required-1", DEV, "TESS", authorization.not_required, service_key="joint_injection"),
    _e("pa-not-required-2", DEV, "QUIL", authorization.not_required, service_key="knee_mri"),
    _e("pa-emergency-1", LOCKED, "TESS", authorization.emergency_department),
    _e("filing-accepted-1", DEV, "TESS", filing.accepted_on_time),
    _e("filing-accepted-2", LOCKED, "QUIL", filing.accepted_on_time),
    _e("filing-primary-payer-1", DEV, "QUIL", filing.primary_payer_first),
    _e("filing-primary-payer-2", LOCKED, "TESS", filing.primary_payer_first),
    _e("filing-earlier-limit-1", DEV, "TESS", filing.earlier_limit_applies),
    _e("diagnosis-denial-wrong-1", DEV, "TESS", coverage.diagnosis_denial_wrong),
    _e("knee-mri-findings-1", DEV, "TESS", coverage.knee_mri_with_findings),
    _e("knee-mri-findings-2", LOCKED, "QUIL", coverage.knee_mri_with_findings),
    _e("hyaluronan-met-1", DEV, "TESS", documentation.hyaluronan, months_of_treatment=4),
    _e(
        "airway-pressure-report-1",
        LOCKED,
        "QUIL",
        documentation.positive_airway_pressure,
        report_on_file=True,
    ),
    # --- REQUEST_DOCUMENTATION: 9 dev, 5 locked ---
    _e("pa-statement-only-1", DEV, "TESS", authorization.statement_only, service_key="knee_mri"),
    _e(
        "pa-statement-only-2",
        LOCKED,
        "QUIL",
        authorization.statement_only,
        service_key="lumbar_mri",
    ),
    _e("side-not-recorded-1", DEV, "TESS", modifiers.side_not_recorded),
    _e("side-not-recorded-2", DEV, "QUIL", modifiers.side_not_recorded),
    _e("filing-sent-only-1", DEV, "TESS", filing.sent_but_not_shown_accepted),
    _e("filing-sent-only-2", LOCKED, "QUIL", filing.sent_but_not_shown_accepted),
    _e("hyaluronan-undated-1", DEV, "TESS", documentation.hyaluronan, months_of_treatment=None),
    _e("hyaluronan-undated-2", DEV, "QUIL", documentation.hyaluronan, months_of_treatment=None),
    _e(
        "airway-pressure-no-report-1",
        DEV,
        "QUIL",
        documentation.positive_airway_pressure,
        report_on_file=False,
    ),
    _e(
        "airway-pressure-no-report-2",
        LOCKED,
        "TESS",
        documentation.positive_airway_pressure,
        report_on_file=False,
    ),
    _e("therapy-progress-1", DEV, "TESS", documentation.therapy_without_progress_note),
    _e("pa-urgent-no-notice-1", LOCKED, "TESS", authorization.urgent_without_notification),
    _e("knee-mri-undated-1", DEV, "QUIL", coverage.knee_mri_undated_treatment),
    _e("knee-mri-undated-2", LOCKED, "TESS", coverage.knee_mri_undated_treatment),
    # --- NO_ACTION: 9 dev, 4 locked ---
    _e("pa-never-requested-1", DEV, "TESS", authorization.never_requested, service_key="knee_mri"),
    _e(
        "pa-never-requested-2",
        DEV,
        "QUIL",
        authorization.never_requested,
        service_key="lumbar_mri",
    ),
    _e(
        "pa-expired-1",
        DEV,
        "TESS",
        authorization.expired,
        service_key="lumbar_mri",
        issued_days_before=75,
    ),
    _e("modifier-25-unsupported-1", DEV, "TESS", modifiers.modifier_25_unsupported, pairing="knee"),
    _e(
        "modifier-25-unsupported-2",
        LOCKED,
        "QUIL",
        modifiers.modifier_25_unsupported,
        pairing="wart",
    ),
    _e("filing-exceeded-1", DEV, "TESS", filing.limit_exceeded, days_late=(15, 40)),
    # 100 to 150 days: late for Quillon's 90, but inside Tessaly's 180.
    _e("filing-exceeded-2", DEV, "QUIL", filing.limit_exceeded, days_late=(10, 60)),
    _e("duplicate-paid-1", DEV, "TESS", duplicates.already_paid),
    _e("duplicate-paid-2", LOCKED, "QUIL", duplicates.already_paid),
    _e("cosmetic-removal-1", DEV, "TESS", coverage.cosmetic_removal),
    _e("hyaluronan-short-1", LOCKED, "QUIL", documentation.hyaluronan, months_of_treatment=4),
    _e("correction-window-passed-1", DEV, "QUIL", modifiers.correction_window_passed),
    _e("knee-mri-osteoarthritis-1", LOCKED, "TESS", coverage.knee_mri_osteoarthritis_only),
    # --- ESCALATE_TO_HUMAN: 7 dev, 4 locked ---
    _e("pa-conflict-1", DEV, "QUIL", authorization.conflicting_clauses, service_key="lumbar_mri"),
    _e(
        "pa-conflict-2",
        LOCKED,
        "QUIL",
        authorization.conflicting_clauses,
        service_key="arthroscopy",
    ),
    _e("modifier-25-borderline-1", DEV, "TESS", modifiers.modifier_25_borderline, pairing="knee"),
    _e("modifier-25-borderline-2", DEV, "QUIL", modifiers.modifier_25_borderline, pairing="wart"),
    _e("side-contradiction-1", DEV, "TESS", modifiers.side_contradiction),
    _e("side-contradiction-2", LOCKED, "QUIL", modifiers.side_contradiction),
    _e("note-other-patient-1", DEV, "TESS", modifiers.note_for_another_patient),
    _e("lumbar-mri-equivocal-1", DEV, "QUIL", coverage.lumbar_mri_equivocal),
    _e("lumbar-mri-equivocal-2", LOCKED, "TESS", coverage.lumbar_mri_equivocal),
    _e("knee-mri-late-addendum-1", DEV, "TESS", coverage.knee_mri_late_addendum),
    _e("duplicate-of-denied-1", LOCKED, "TESS", duplicates.duplicate_of_unexplained_denial),
    # --- Invalid input: 6 dev, 2 locked ---
    _e("invalid-npi-1", DEV, "TESS", invalid.invalid_input, defect="npi_check_digit"),
    _e("invalid-diagnosis-1", DEV, "QUIL", invalid.invalid_input, defect="diagnosis_without_dot"),
    _e("invalid-total-1", DEV, "TESS", invalid.invalid_input, defect="total_mismatch"),
    _e("invalid-dates-1", DEV, "QUIL", invalid.invalid_input, defect="submitted_before_service"),
    _e(
        "invalid-denial-claim-1",
        DEV,
        "TESS",
        invalid.invalid_input,
        defect="denial_for_other_claim",
    ),
    _e("invalid-pointer-1", DEV, "QUIL", invalid.invalid_input, defect="pointer_out_of_range"),
    _e(
        "invalid-denied-line-1", LOCKED, "TESS", invalid.invalid_input, defect="denied_line_missing"
    ),
    _e("invalid-group-code-1", LOCKED, "QUIL", invalid.invalid_input, defect="unknown_group_code"),
)
