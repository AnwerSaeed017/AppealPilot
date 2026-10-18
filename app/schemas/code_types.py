"""Field types for identifiers, billing codes and money.

Each format rule is defined here once and reused by every schema. The patterns check
shape only; whether a code exists in a code set is a rules-engine question.
"""

from decimal import Decimal
from typing import Annotated

from pydantic import AfterValidator, BeforeValidator, Field, StringConstraints


def _trim_and_upper(value: object) -> object:
    return value.strip().upper() if isinstance(value, str) else value


# Normalise first, then match: StringConstraints alone checks the pattern before it
# changes case, so "m17.11" would be rejected instead of normalised.
_normalise = BeforeValidator(_trim_and_upper)


def _code(pattern: str) -> StringConstraints:
    return StringConstraints(pattern=pattern)


# An NPI is checked as a card number would be: prefix it with the health-industry
# issuer number, then the whole string must pass the Luhn check.
_NPI_LUHN_PREFIX = "80840"


def _check_npi_digit(value: str) -> str:
    total = 0
    for position, character in enumerate(reversed(_NPI_LUHN_PREFIX + value)):
        digit = int(character)
        if position % 2 == 1:
            digit = digit * 2 - 9 if digit > 4 else digit * 2
        total += digit
    if total % 10 != 0:
        raise ValueError("NPI check digit is not valid")
    return value


_PAYER = r"[A-Z][A-Z0-9]{1,11}"
_POLICY = rf"{_PAYER}-[A-Z][A-Z0-9]{{0,11}}"

# Identifiers
PayerId = Annotated[str, _normalise, _code(rf"^{_PAYER}$")]
PolicyId = Annotated[str, _normalise, _code(rf"^{_POLICY}$")]
# Policy ID plus a dotted section number, for example ACME-PA-4.2.
ClauseId = Annotated[str, _normalise, _code(rf"^{_POLICY}-[0-9]{{1,3}}(\.[0-9]{{1,3}}){{0,3}}$")]
ClaimId = Annotated[str, _normalise, _code(r"^[A-Z0-9][A-Z0-9-]{0,37}$")]
MemberId = Annotated[str, _normalise, _code(r"^[A-Z0-9][A-Z0-9-]{0,19}$")]
PatientId = Annotated[str, _normalise, _code(r"^[A-Z0-9][A-Z0-9-]{0,37}$")]
Npi = Annotated[str, _normalise, _code(r"^[0-9]{10}$"), AfterValidator(_check_npi_digit)]
PriorAuthorizationNumber = Annotated[str, _normalise, _code(r"^[A-Z0-9][A-Z0-9-]{0,29}$")]
# How a citation names a supporting document. "NOTE" is reserved for the visit note.
DocumentId = Annotated[str, _normalise, _code(r"^[A-Z][A-Z0-9-]{0,19}$")]
VISIT_NOTE_DOCUMENT_ID = "NOTE"

# Billing codes
# ICD-10-CM: letter, digit, digit or A/B, then up to four more characters after a dot.
IcdCode = Annotated[str, _normalise, _code(r"^[A-Z][0-9][0-9AB](\.[0-9A-Z]{1,4})?$")]
# CPT Category I (5 digits), Category II/III (4 digits and F, T or U), or HCPCS Level II.
ProcedureCode = Annotated[str, _normalise, _code(r"^([0-9]{5}|[0-9]{4}[FTU]|[A-V][0-9]{4})$")]
ModifierCode = Annotated[str, _normalise, _code(r"^[A-Z0-9]{2}$")]
PlaceOfServiceCode = Annotated[str, _normalise, _code(r"^[0-9]{2}$")]
# Claim Adjustment Reason Code: 1 to 3 digits, or a letter and 1 to 2 digits.
CarcCode = Annotated[str, _normalise, _code(r"^([0-9]{1,3}|[A-Z][0-9]{1,2})$")]
# Remittance Advice Remark Code: M, MA or N followed by digits.
RarcCode = Annotated[str, _normalise, _code(r"^(MA|M|N)[0-9]{1,4}$")]

LineNumber = Annotated[int, Field(ge=1, le=50)]
# Where a policy clause was published, for clauses taken from a real source.
SourceUrl = Annotated[str, StringConstraints(pattern=r"^https://\S+$", max_length=500)]
Money = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]
