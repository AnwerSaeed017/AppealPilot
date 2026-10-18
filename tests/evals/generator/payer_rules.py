"""Where each rule lives in each payer's policies, and the limits that differ.

Scenarios name a rule by meaning ("the clause on side modifiers") and read the clause
ID and any number from here, so one scenario can be written once for both payers.
A test checks every clause ID in this table against the policy files.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PayerRules:
    name: str

    # Prior authorization
    pa_services: str
    pa_number_required: str
    pa_validity: str
    pa_validity_days: int
    pa_number_omitted: str
    pa_urgent: str
    pa_none_after_service: str
    pa_appeal: str

    # Modifiers
    modifier_25: str
    modifier_25_record: str
    modifier_25_not_allowed: str
    side_modifier: str
    side_modifier_fix: str
    corrected_claim_limit: str
    corrected_claim_days: int

    # Timely filing
    filing_limit: str
    filing_limit_days: int
    filing_exceptions: str
    filing_proof: str
    filing_final: str
    primary_eob_days: int

    # Duplicates
    duplicate_definition: str
    duplicate_paid: str
    duplicate_repeat: str
    duplicate_replacement: str

    # Documentation
    documentation_deadline: str
    documentation_deadline_days: int
    documentation_acceptable: str
    documentation_absent: str
    cpap: str
    hyaluronan: str
    hyaluronan_months: int

    # Coverage
    diagnosis_support: str
    diagnosis_fix: str
    knee_mri: str
    knee_mri_weeks: int
    lumbar_mri: str
    joint_injection: str
    necessity_denial: str
    necessity_appeal: str


RULES: dict[str, PayerRules] = {
    "TESS": PayerRules(
        name="Tessaly Health Plan",
        pa_services="TESS-PA-1.1",
        pa_number_required="TESS-PA-1.2",
        pa_validity="TESS-PA-2.1",
        pa_validity_days=60,
        pa_number_omitted="TESS-PA-3.1",
        pa_urgent="TESS-PA-3.2",
        pa_none_after_service="TESS-PA-3.3",
        pa_appeal="TESS-PA-4.1",
        modifier_25="TESS-MOD-1.1",
        modifier_25_record="TESS-MOD-1.2",
        modifier_25_not_allowed="TESS-MOD-1.3",
        side_modifier="TESS-MOD-2.1",
        side_modifier_fix="TESS-MOD-2.2",
        corrected_claim_limit="TESS-MOD-4.1",
        corrected_claim_days=90,
        filing_limit="TESS-TF-1.1",
        filing_limit_days=180,
        filing_exceptions="TESS-TF-2.1",
        filing_proof="TESS-TF-2.2",
        filing_final="TESS-TF-3.1",
        primary_eob_days=90,
        duplicate_definition="TESS-DUP-1.1",
        duplicate_paid="TESS-DUP-1.2",
        duplicate_repeat="TESS-DUP-2.1",
        duplicate_replacement="TESS-DUP-2.2",
        documentation_deadline="TESS-DOC-1.1",
        documentation_deadline_days=45,
        documentation_acceptable="TESS-DOC-1.2",
        documentation_absent="TESS-DOC-3.1",
        cpap="TESS-DOC-2.1",
        hyaluronan="TESS-DOC-2.2",
        hyaluronan_months=3,
        diagnosis_support="TESS-COV-1.1",
        diagnosis_fix="TESS-COV-1.2",
        knee_mri="TESS-COV-2.1",
        knee_mri_weeks=6,
        lumbar_mri="TESS-COV-2.2",
        joint_injection="TESS-COV-2.3",
        necessity_denial="TESS-COV-4.1",
        necessity_appeal="TESS-APL-3.1",
    ),
    "QUIL": PayerRules(
        name="Quillon Mutual",
        pa_services="QUIL-PA-1.1",
        pa_number_required="QUIL-PA-1.2",
        pa_validity="QUIL-PA-2.1",
        pa_validity_days=90,
        pa_number_omitted="QUIL-PA-2.2",
        pa_urgent="QUIL-PA-3.1",
        pa_none_after_service="QUIL-PA-3.2",
        pa_appeal="QUIL-PA-4.1",
        modifier_25="QUIL-MOD-1.1",
        modifier_25_record="QUIL-MOD-1.2",
        modifier_25_not_allowed="QUIL-MOD-1.2",
        side_modifier="QUIL-MOD-2.1",
        side_modifier_fix="QUIL-MOD-2.2",
        corrected_claim_limit="QUIL-MOD-3.1",
        corrected_claim_days=60,
        filing_limit="QUIL-TF-1.1",
        filing_limit_days=90,
        filing_exceptions="QUIL-TF-2.1",
        filing_proof="QUIL-TF-2.2",
        filing_final="QUIL-TF-3.1",
        primary_eob_days=60,
        duplicate_definition="QUIL-DUP-1.1",
        duplicate_paid="QUIL-DUP-1.2",
        duplicate_repeat="QUIL-DUP-2.1",
        duplicate_replacement="QUIL-DUP-2.2",
        documentation_deadline="QUIL-DOC-1.1",
        documentation_deadline_days=30,
        documentation_acceptable="QUIL-DOC-1.2",
        documentation_absent="QUIL-DOC-3.1",
        cpap="QUIL-DOC-2.1",
        hyaluronan="QUIL-DOC-2.2",
        hyaluronan_months=6,
        diagnosis_support="QUIL-COV-1.1",
        diagnosis_fix="QUIL-COV-1.2",
        knee_mri="QUIL-COV-2.1",
        knee_mri_weeks=4,
        lumbar_mri="QUIL-COV-2.2",
        joint_injection="QUIL-COV-2.3",
        necessity_denial="QUIL-COV-3.1",
        necessity_appeal="QUIL-APL-3.1",
    ),
}
