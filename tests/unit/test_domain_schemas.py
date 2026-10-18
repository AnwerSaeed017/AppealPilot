from decimal import Decimal
from typing import Any

import pytest
from pydantic import ValidationError

from app.schemas.case_input import CaseInput
from app.schemas.claim import Claim
from app.schemas.denial import ClaimAdjustmentGroup, Denial
from app.schemas.policy_clause import PolicyClause
from tests.samples import (
    case_input_payload,
    claim_payload,
    denial_payload,
    policy_clause_payload,
)


def test_sample_case_validates() -> None:
    case = CaseInput.model_validate(case_input_payload())

    assert case.claim.total_charge == Decimal("325.00")
    assert case.claim.lines[1].modifiers == ("RT",)
    assert case.denial.group_code is ClaimAdjustmentGroup.CONTRACTUAL_OBLIGATION
    assert case.denial.denied_line_numbers == (2,)


def test_codes_are_trimmed_and_upper_cased() -> None:
    payload = claim_payload()
    payload["diagnosis_codes"] = [" m17.11 ", "e11.9"]
    payload["lines"][1]["modifiers"] = ["rt"]

    claim = Claim.model_validate(payload)

    assert claim.diagnosis_codes == ("M17.11", "E11.9")
    assert claim.lines[1].modifiers == ("RT",)


def test_schemas_are_immutable_and_reject_unknown_fields() -> None:
    claim = Claim.model_validate(claim_payload())
    with pytest.raises(ValidationError):
        claim.claim_id = "OTHER"  # type: ignore[misc]

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        Claim.model_validate(claim_payload() | {"case_id": "set-by-client"})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("billing_provider_npi", "12345"),
        ("billing_provider_npi", "1234567890"),
        ("payer_id", "acme health"),
        ("place_of_service", "office"),
        ("diagnosis_codes", ["17.11"]),
        ("diagnosis_codes", ["M1711"]),
        ("diagnosis_codes", []),
        ("diagnosis_codes", ["M17.11", "M17.11"]),
        ("total_charge", "-1.00"),
        ("total_charge", "325.001"),
        ("lines", []),
    ],
)
def test_claim_rejects_malformed_fields(field: str, value: Any) -> None:
    with pytest.raises(ValidationError):
        Claim.model_validate(claim_payload() | {field: value})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("procedure_code", "9921"),
        ("procedure_code", "X12345"),
        ("modifiers", ["250"]),
        ("modifiers", ["25", "25"]),
        ("modifiers", ["25", "59", "RT", "LT", "76"]),
        ("diagnosis_pointers", []),
        ("diagnosis_pointers", [0]),
        ("diagnosis_pointers", [3]),
        ("units", 0),
    ],
)
def test_claim_rejects_malformed_lines(field: str, value: Any) -> None:
    payload = claim_payload()
    payload["lines"][0][field] = value

    with pytest.raises(ValidationError):
        Claim.model_validate(payload)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"total_charge": "300.00"}, "sum of the line charges"),
        ({"submitted_date": "2026-06-01"}, "before a service date"),
        ({"patient_date_of_birth": "2026-07-01"}, "after a service date"),
        ({"original_claim_id": "CLM-2026-000123"}, "different claim"),
    ],
)
def test_claim_rejects_inconsistent_values(changes: dict[str, Any], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        Claim.model_validate(claim_payload() | changes)


def test_claim_rejects_duplicate_line_numbers() -> None:
    payload = claim_payload()
    payload["lines"][1]["line_number"] = 1

    with pytest.raises(ValidationError, match="line numbers must be unique"):
        Claim.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("group_code", "XX"),
        ("carc_code", "1977"),
        ("carc_code", "CO-197"),
        ("rarc_codes", ["X54"]),
        ("rarc_codes", ["N54", "N54"]),
        ("denied_line_numbers", [2, 2]),
        ("payer_remark", ""),
    ],
)
def test_denial_rejects_malformed_fields(field: str, value: Any) -> None:
    with pytest.raises(ValidationError):
        Denial.model_validate(denial_payload() | {field: value})


@pytest.mark.parametrize("carc_code", ["4", "16", "197", "A1", "B13"])
def test_denial_accepts_carc_shapes(carc_code: str) -> None:
    denial = Denial.model_validate(denial_payload() | {"carc_code": carc_code})

    assert denial.carc_code == carc_code


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"claim_id": "CLM-OTHER"}, "different claim"),
        ({"payer_id": "ZENITH"}, "different payer"),
        ({"denied_line_numbers": [7]}, "not on the claim"),
        ({"denial_date": "2026-06-01"}, "before the claim was submitted"),
        ({"denied_amount": "900.00"}, "must not exceed"),
    ],
)
def test_case_input_rejects_a_denial_that_does_not_match(
    changes: dict[str, Any], message: str
) -> None:
    payload = case_input_payload()
    payload["denial"] |= changes

    with pytest.raises(ValidationError, match=message):
        CaseInput.model_validate(payload)


def test_policy_clause_validates() -> None:
    clause = PolicyClause.model_validate(policy_clause_payload())

    assert clause.clause_id == "ACME-PA-4.2"
    assert clause.effective_to is None


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"clause_id": "ACME-PA"}, "String should match pattern"),
        ({"clause_id": "ACME-TF-4.2"}, "clause_id must start with the policy_id"),
        ({"payer_id": "ZENITH"}, "policy_id must start with the payer_id"),
        ({"effective_to": "2025-12-31"}, "effective_to must not be before"),
    ],
)
def test_policy_clause_rejects_inconsistent_ids_and_dates(
    changes: dict[str, Any], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        PolicyClause.model_validate(policy_clause_payload() | changes)
