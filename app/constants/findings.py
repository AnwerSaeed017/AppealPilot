"""Groups of findings that rules and services act on."""

from app.schemas.finding import FindingCode

# Errors in the claim itself that a corrected claim or a reopening can fix.
CORRECTABLE_FINDINGS: frozenset[FindingCode] = frozenset(
    {
        FindingCode.SIDE_MODIFIER_MISSING,
        FindingCode.VISIT_WITHOUT_MODIFIER_25,
        FindingCode.REPEATED_LINE_WITHOUT_REPEAT_MODIFIER,
        FindingCode.AUTHORIZATION_NUMBER_MISSING,
    }
)

# Findings that show the payer's stated reason does not hold for this claim.
PAYER_ERROR_FINDINGS: frozenset[FindingCode] = frozenset(
    {
        FindingCode.AUTHORIZATION_NOT_REQUIRED,
        FindingCode.FILED_WITHIN_LIMIT,
    }
)

# Findings that put a case beyond what the workflow may decide. When one is present the
# case goes to a person, whatever triage chose.
ESCALATION_FINDINGS: frozenset[FindingCode] = frozenset(
    {
        FindingCode.LATERALITY_CONTRADICTION,
        FindingCode.DOCUMENT_PATIENT_MISMATCH,
        FindingCode.LATE_ENTRY_AFTER_DENIAL,
    }
)
