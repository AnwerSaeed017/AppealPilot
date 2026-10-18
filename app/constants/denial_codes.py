"""Claim adjustment reason codes (CARC) that the rules act on."""

MODIFIER_PROBLEM = "4"
DIAGNOSIS_INCONSISTENT = "11"
DUPLICATE_CLAIM = "18"
FILING_LIMIT_EXPIRED = "29"
NOT_MEDICALLY_NECESSARY = "50"
INCLUDED_IN_ANOTHER_SERVICE = "97"
FREQUENCY_NOT_SUPPORTED = "151"
AUTHORIZATION_ABSENT = "197"
DOCUMENTATION_REQUIRED = "252"

# Denials that turn on clinical support, with the question each one raises.
CLINICAL_DENIAL_QUESTIONS: dict[str, str] = {
    DIAGNOSIS_INCONSISTENT: "whether the diagnosis supports the procedure",
    NOT_MEDICALLY_NECESSARY: "whether the service was medically necessary",
    FREQUENCY_NOT_SUPPORTED: "whether the record supports providing the service this often",
}

# Denials decided by the conditions a policy sets for the procedure itself.
PROCEDURE_CONDITION_DENIALS: frozenset[str] = frozenset(
    {
        DIAGNOSIS_INCONSISTENT,
        NOT_MEDICALLY_NECESSARY,
        DOCUMENTATION_REQUIRED,
        FREQUENCY_NOT_SUPPORTED,
    }
)

# What each reason code means, in our own words. Used to describe a denial in a search.
DENIAL_DESCRIPTIONS: dict[str, str] = {
    MODIFIER_PROBLEM: "required modifier missing or modifier inconsistent with the procedure",
    DIAGNOSIS_INCONSISTENT: "diagnosis inconsistent with the procedure",
    DUPLICATE_CLAIM: "duplicate of a claim or service already processed",
    FILING_LIMIT_EXPIRED: "time limit for filing the claim has expired",
    NOT_MEDICALLY_NECESSARY: "service not deemed medically necessary",
    FREQUENCY_NOT_SUPPORTED: "service provided more often than the payer's frequency limit",
    INCLUDED_IN_ANOTHER_SERVICE: (
        "visit or service included in the payment for another procedure on the same day"
    ),
    AUTHORIZATION_ABSENT: "prior authorization absent",
    DOCUMENTATION_REQUIRED: "additional documentation required",
}
