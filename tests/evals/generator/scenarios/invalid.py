"""Malformed submissions that must be rejected before any model is called."""

from datetime import timedelta
from decimal import Decimal
from typing import Any

from tests.evals.generator.kit import Built, Kit
from tests.evals.generator.payer_rules import PayerRules
from tests.evals.generator.scenarios.modifiers import side_missing_documented


def _npi_check_digit(payload: dict[str, Any], kit: Kit) -> str:
    npi = payload["claim"]["billing_provider_npi"]
    payload["claim"]["billing_provider_npi"] = npi[:-1] + str((int(npi[-1]) + 1) % 10)
    return "The billing provider NPI has ten digits but its check digit is wrong."


def _diagnosis_without_dot(payload: dict[str, Any], kit: Kit) -> str:
    code = payload["claim"]["diagnosis_codes"][0]
    payload["claim"]["diagnosis_codes"][0] = code.replace(".", "")
    return "A diagnosis code is written without its decimal point."


def _total_mismatch(payload: dict[str, Any], kit: Kit) -> str:
    total = Decimal(payload["claim"]["total_charge"]) + Decimal("10.00")
    payload["claim"]["total_charge"] = str(total)
    return "The claim total does not equal the sum of its line charges."


def _submitted_before_service(payload: dict[str, Any], kit: Kit) -> str:
    payload["claim"]["submitted_date"] = (kit.dos - timedelta(days=3)).isoformat()
    return "The claim is dated as submitted before the service took place."


def _denial_for_other_claim(payload: dict[str, Any], kit: Kit) -> str:
    payload["denial"]["claim_id"] = kit.new_claim_id()
    return "The denial refers to a different claim number from the claim submitted."


def _pointer_out_of_range(payload: dict[str, Any], kit: Kit) -> str:
    payload["claim"]["lines"][0]["diagnosis_pointers"] = [4]
    return "A line points to a fourth diagnosis, but the claim lists only one."


def _denied_line_missing(payload: dict[str, Any], kit: Kit) -> str:
    payload["denial"]["denied_line_numbers"] = [9]
    return "The denial names line 9, which is not on the claim."


def _unknown_group_code(payload: dict[str, Any], kit: Kit) -> str:
    payload["denial"]["group_code"] = "ZZ"
    return "The denial's group code is not one of CO, PR, OA or PI."


_DEFECTS = {
    "npi_check_digit": _npi_check_digit,
    "diagnosis_without_dot": _diagnosis_without_dot,
    "total_mismatch": _total_mismatch,
    "submitted_before_service": _submitted_before_service,
    "denial_for_other_claim": _denial_for_other_claim,
    "pointer_out_of_range": _pointer_out_of_range,
    "denied_line_missing": _denied_line_missing,
    "unknown_group_code": _unknown_group_code,
}


def invalid_input(kit: Kit, rules: PayerRules, defect: str) -> Built:
    """An otherwise ordinary case with one field broken."""
    valid = side_missing_documented(kit, rules)
    reason = _DEFECTS[defect](valid.input, kit)

    return Built(
        input=valid.input,
        as_of_date=valid.as_of_date,
        action=None,
        rationale=f"{reason} The case must stop at validation, with no model call.",
        tags=("invalid_input",),
    )
