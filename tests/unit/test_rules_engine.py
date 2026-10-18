"""The rules engine, checked two ways: against small hand-built cases, and against
the development cases, where each scenario says which facts the rules must find.

Only the development cases are used here. The locked cases are for release runs.
"""

import copy
import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from dependency_injector import providers

from app.containers.container import Container
from app.core.exceptions import ValidationFailedError
from app.core.settings import Settings
from app.interfaces.service.rules_engine_service import IRulesEngineService
from app.schemas.case_input import CaseInput
from app.schemas.eval_case import EvalCase, EvalSplit
from app.schemas.finding import Finding
from app.schemas.finding import FindingCode as F
from tests.evals.generator.build import build_cases
from tests.evals.generator.payer_rules import RULES

AS_OF = date(2026, 7, 1)


@pytest.fixture(scope="module")
def engine() -> IRulesEngineService:
    container = Container()
    container.settings.override(
        providers.Object(
            Settings(
                _env_file=None,
                database_url="sqlite+aiosqlite:///:memory:",
                policies_dir=Path("seeders/policies"),
            )
        )
    )
    service: IRulesEngineService = container.services.rules_engine_service()
    return service


def codes(findings: tuple[Finding, ...]) -> set[F]:
    return {finding.code for finding in findings}


# --- Hand-built cases ---------------------------------------------------------


def base_case() -> dict[str, Any]:
    """A Tessaly knee injection, billed correctly, denied for a missing modifier."""
    return {
        "claim": {
            "claim_id": "CLM-1",
            "payer_id": "TESS",
            "member_id": "TESS-1",
            "patient_id": "PT-1",
            "patient_date_of_birth": "1960-01-01",
            "billing_provider_npi": "1234567893",
            "place_of_service": "11",
            "submitted_date": "2026-06-10",
            "diagnosis_codes": ["M17.11"],
            "lines": [
                {
                    "line_number": 1,
                    "service_date": "2026-06-01",
                    "procedure_code": "20610",
                    "modifiers": ["RT"],
                    "diagnosis_pointers": [1],
                    "units": 1,
                    "charge_amount": "140.00",
                }
            ],
            "total_charge": "140.00",
        },
        "denial": {
            "claim_id": "CLM-1",
            "payer_id": "TESS",
            "group_code": "CO",
            "carc_code": "4",
            "denial_date": "2026-06-20",
            "denied_amount": "140.00",
        },
        "visit_note": {"encounter_date": "2026-06-01", "text": "Right knee injected."},
    }


async def findings_for(
    engine: IRulesEngineService, payload: dict[str, Any], as_of: date = AS_OF
) -> tuple[Finding, ...]:
    return await engine.evaluate(CaseInput.model_validate(payload), as_of)


async def test_a_clean_case_produces_no_findings(engine: IRulesEngineService) -> None:
    assert await findings_for(engine, base_case()) == ()


async def test_unknown_payer_is_rejected(engine: IRulesEngineService) -> None:
    payload = base_case()
    payload["claim"]["payer_id"] = payload["denial"]["payer_id"] = "NOPE"

    with pytest.raises(ValidationFailedError, match="Unknown payer NOPE"):
        await findings_for(engine, payload)


@pytest.mark.parametrize(
    ("submitted", "expected"),
    [("2026-11-28", set()), ("2026-11-29", {F.FILING_LIMIT_EXCEEDED})],
)
async def test_filing_limit_is_exceeded_only_after_the_last_day(
    engine: IRulesEngineService, submitted: str, expected: set[F]
) -> None:
    payload = base_case()
    payload["claim"]["submitted_date"] = submitted  # day 180, then day 181
    payload["denial"]["denial_date"] = "2026-12-05"

    found = await findings_for(engine, payload, as_of=date(2026, 12, 10))

    assert codes(found) == expected


async def test_filing_finding_cites_the_clause_and_the_numbers(
    engine: IRulesEngineService,
) -> None:
    payload = base_case()
    payload["claim"]["submitted_date"] = "2026-12-20"
    payload["denial"]["denial_date"] = "2026-12-28"

    (finding,) = await findings_for(engine, payload, as_of=date(2027, 1, 5))

    assert finding.clause_ids == ("TESS-TF-1.1",)
    assert "202 days" in finding.message
    assert "180 days" in finding.message


async def test_earlier_limit_applies_to_services_before_the_cut_off(
    engine: IRulesEngineService,
) -> None:
    payload = base_case()
    payload["claim"]["lines"][0]["service_date"] = "2025-10-01"
    payload["visit_note"]["encounter_date"] = "2025-10-01"
    payload["claim"]["submitted_date"] = "2026-06-10"  # 252 days: over 180, under 365
    payload["denial"]["carc_code"] = "29"

    (finding,) = await findings_for(engine, payload)

    assert finding.code is F.FILED_WITHIN_LIMIT
    assert finding.clause_ids == ("TESS-TF-1.2",)


async def test_the_same_delay_is_late_for_one_payer_and_on_time_for_the_other(
    engine: IRulesEngineService,
) -> None:
    tessaly = base_case()
    tessaly["claim"]["submitted_date"] = "2026-09-20"  # 111 days
    tessaly["denial"]["denial_date"] = "2026-09-28"
    quillon = copy.deepcopy(tessaly)
    quillon["claim"]["payer_id"] = quillon["denial"]["payer_id"] = "QUIL"
    as_of = date(2026, 10, 1)

    assert F.FILING_LIMIT_EXCEEDED not in codes(await findings_for(engine, tessaly, as_of))
    assert F.FILING_LIMIT_EXCEEDED in codes(await findings_for(engine, quillon, as_of))


@pytest.mark.parametrize(
    ("as_of", "expected"),
    [
        (date(2026, 9, 18), set()),  # day 90
        (date(2026, 9, 19), {F.CORRECTED_CLAIM_WINDOW_CLOSED}),  # day 91
        (date(2026, 12, 17), {F.CORRECTED_CLAIM_WINDOW_CLOSED}),  # day 180
        (date(2026, 12, 18), {F.CORRECTED_CLAIM_WINDOW_CLOSED, F.APPEAL_WINDOW_CLOSED}),
    ],
)
async def test_response_windows_close_the_day_after_their_limit(
    engine: IRulesEngineService, as_of: date, expected: set[F]
) -> None:
    assert codes(await findings_for(engine, base_case(), as_of)) == expected


def with_prior(payload: dict[str, Any], outcome: str, **changes: Any) -> dict[str, Any]:
    prior_line = copy.deepcopy(payload["claim"]["lines"][0]) | changes
    prior: dict[str, Any] = {
        "claim_id": "CLM-0",
        "received_date": "2026-06-05",
        "outcome": outcome,
        "lines": [prior_line],
    }
    payload["prior_claims"] = [prior]
    payload["denial"]["carc_code"] = "18"
    return payload


async def test_duplicate_of_a_paid_line(engine: IRulesEngineService) -> None:
    (finding,) = await findings_for(engine, with_prior(base_case(), "PAID"))

    assert finding.code is F.DUPLICATE_OF_PAID_CLAIM
    assert finding.clause_ids == ("TESS-DUP-1.2",)
    assert "CLM-0" in finding.message


async def test_duplicate_of_a_denied_line_reports_what_is_known_of_the_reason(
    engine: IRulesEngineService,
) -> None:
    (finding,) = await findings_for(engine, with_prior(base_case(), "DENIED"))

    assert finding.code is F.DUPLICATE_OF_DENIED_CLAIM
    assert "no reason code on file" in finding.message


async def test_changed_claim_sent_as_new_is_recognised(engine: IRulesEngineService) -> None:
    (finding,) = await findings_for(engine, with_prior(base_case(), "DENIED", modifiers=[]))

    assert finding.code is F.CHANGED_VERSION_OF_PRIOR_CLAIM
    assert finding.clause_ids == ("TESS-DUP-2.2",)


async def test_a_proper_replacement_is_not_flagged(engine: IRulesEngineService) -> None:
    payload = with_prior(base_case(), "DENIED", modifiers=[])
    payload["claim"]["original_claim_id"] = "CLM-0"

    assert codes(await findings_for(engine, payload)) == {F.NO_MATCHING_PRIOR_CLAIM}


async def test_duplicate_denial_with_nothing_on_file(engine: IRulesEngineService) -> None:
    payload = base_case()
    payload["denial"]["carc_code"] = "18"

    assert codes(await findings_for(engine, payload)) == {F.NO_MATCHING_PRIOR_CLAIM}


async def test_side_modifier_missing(engine: IRulesEngineService) -> None:
    payload = base_case()
    payload["claim"]["lines"][0]["modifiers"] = []

    (finding,) = await findings_for(engine, payload)

    assert finding.code is F.SIDE_MODIFIER_MISSING
    assert finding.line_numbers == (1,)


def as_service(payload: dict[str, Any], code: str, charge: str) -> dict[str, Any]:
    line = payload["claim"]["lines"][0]
    line["procedure_code"], line["charge_amount"] = code, charge
    payload["claim"]["total_charge"] = payload["denial"]["denied_amount"] = charge
    payload["denial"]["carc_code"] = "197"
    return payload


async def test_authorization_number_missing_for_a_listed_service(
    engine: IRulesEngineService,
) -> None:
    (finding,) = await findings_for(engine, as_service(base_case(), "73721", "620.00"))

    assert finding.code is F.AUTHORIZATION_NUMBER_MISSING
    assert finding.clause_ids == ("TESS-PA-1.1", "TESS-PA-1.2")


async def test_authorization_number_present_is_not_a_finding(
    engine: IRulesEngineService,
) -> None:
    payload = as_service(base_case(), "73721", "620.00")
    payload["claim"]["prior_authorization_number"] = "AU-1"

    assert await findings_for(engine, payload) == ()


async def test_the_authorization_list_differs_by_payer(engine: IRulesEngineService) -> None:
    payload = as_service(base_case(), "73721", "620.00")
    payload["claim"]["payer_id"] = payload["denial"]["payer_id"] = "QUIL"

    (finding,) = await findings_for(engine, payload)

    assert finding.code is F.AUTHORIZATION_NOT_REQUIRED
    assert finding.clause_ids == ("QUIL-PA-1.1",)


async def test_emergency_department_is_exempt_for_tessaly_only(
    engine: IRulesEngineService,
) -> None:
    tessaly = as_service(base_case(), "72148", "710.00")
    tessaly["claim"]["lines"][0]["modifiers"] = []
    tessaly["claim"]["place_of_service"] = "23"
    quillon = copy.deepcopy(tessaly)
    quillon["claim"]["payer_id"] = quillon["denial"]["payer_id"] = "QUIL"

    (exempt,) = await findings_for(engine, tessaly)

    assert exempt.code is F.AUTHORIZATION_NOT_REQUIRED
    assert exempt.clause_ids == ("TESS-PA-3.2",)
    assert codes(await findings_for(engine, quillon)) == {F.AUTHORIZATION_NUMBER_MISSING}


def with_visit(payload: dict[str, Any], modifiers: list[str]) -> dict[str, Any]:
    payload["claim"]["lines"].append(
        {
            "line_number": 2,
            "service_date": "2026-06-01",
            "procedure_code": "99213",
            "modifiers": modifiers,
            "diagnosis_pointers": [1],
            "units": 1,
            "charge_amount": "135.00",
        }
    )
    payload["claim"]["total_charge"] = "275.00"
    return payload


async def test_visit_with_procedure_and_no_modifier_25(engine: IRulesEngineService) -> None:
    (finding,) = await findings_for(engine, with_visit(base_case(), []))

    assert finding.code is F.VISIT_WITHOUT_MODIFIER_25
    assert finding.line_numbers == (2,)
    assert "needs review" in finding.message


async def test_visit_with_modifier_25_is_not_a_finding(engine: IRulesEngineService) -> None:
    assert await findings_for(engine, with_visit(base_case(), ["25"])) == ()


async def test_note_dated_on_another_day(engine: IRulesEngineService) -> None:
    payload = base_case()
    payload["visit_note"]["encounter_date"] = "2026-05-30"

    assert codes(await findings_for(engine, payload)) == {F.NOTE_DATE_MISMATCH}


@pytest.mark.parametrize("carc_code", ["11", "50"])
async def test_clinical_denials_are_marked_for_review(
    engine: IRulesEngineService, carc_code: str
) -> None:
    payload = base_case()
    payload["denial"]["carc_code"] = carc_code

    found = await findings_for(engine, payload)

    assert codes(found) == {F.CLINICAL_SUPPORT_NEEDS_REVIEW, F.PROCEDURE_CONDITIONS_CLAUSE}


@pytest.mark.parametrize(
    ("payer_id", "clause_id"), [("TESS", "TESS-COV-2.3"), ("QUIL", "QUIL-COV-2.3")]
)
async def test_procedure_conditions_clause_is_the_payers_own(
    engine: IRulesEngineService, payer_id: str, clause_id: str
) -> None:
    payload = base_case()
    payload["claim"]["payer_id"] = payload["denial"]["payer_id"] = payer_id
    payload["denial"]["carc_code"] = "50"

    found = await findings_for(engine, payload)

    (named,) = [f for f in found if f.code is F.PROCEDURE_CONDITIONS_CLAUSE]
    assert named.clause_ids == (clause_id,)
    assert named.line_numbers == (1,)


async def test_procedure_conditions_clause_is_not_named_for_other_denials(
    engine: IRulesEngineService,
) -> None:
    # The base case is a modifier denial on a procedure that has a conditions clause.
    assert await findings_for(engine, base_case()) == ()


# --- The development cases ----------------------------------------------------

# For each scenario, the exact set of findings the rules must produce. Scenarios the
# rules have nothing to say about are listed with an empty set, so a new finding
# appearing there fails the test and has to be looked at.
EXPECTED_BY_SCENARIO: dict[str, set[F]] = {
    "pa-number-omitted": {F.AUTHORIZATION_NUMBER_MISSING},
    "pa-statement-only": {F.AUTHORIZATION_NUMBER_MISSING},
    "pa-never-requested": {F.AUTHORIZATION_NUMBER_MISSING},
    "pa-conflict": {F.AUTHORIZATION_NUMBER_MISSING},
    "pa-not-required": {F.AUTHORIZATION_NOT_REQUIRED},
    "pa-no-record": set(),
    "pa-expired": set(),
    "side-missing": {F.SIDE_MODIFIER_MISSING},
    "side-not-recorded": {F.SIDE_MODIFIER_MISSING},
    "side-contradiction": {F.SIDE_MODIFIER_MISSING},
    "note-other-patient": {F.SIDE_MODIFIER_MISSING},
    "correction-window-passed": {F.SIDE_MODIFIER_MISSING, F.CORRECTED_CLAIM_WINDOW_CLOSED},
    "side-wrong": set(),
    "modifier-25-supported": {F.VISIT_WITHOUT_MODIFIER_25},
    "modifier-25-unsupported": {F.VISIT_WITHOUT_MODIFIER_25},
    "modifier-25-borderline": {F.VISIT_WITHOUT_MODIFIER_25},
    "filing-exceeded": {F.FILING_LIMIT_EXCEEDED},
    "filing-accepted": {F.FILING_LIMIT_EXCEEDED},
    "filing-sent-only": {F.FILING_LIMIT_EXCEEDED},
    "filing-primary-payer": {F.FILING_LIMIT_EXCEEDED},
    "filing-earlier-limit": {F.FILED_WITHIN_LIMIT},
    "duplicate-paid": {F.DUPLICATE_OF_PAID_CLAIM},
    "duplicate-sent-as-new": {F.CHANGED_VERSION_OF_PRIOR_CLAIM},
    "duplicate-repeat": {F.REPEATED_LINE_WITHOUT_REPEAT_MODIFIER, F.NO_MATCHING_PRIOR_CLAIM},
    "diagnosis-pointer": {F.CLINICAL_SUPPORT_NEEDS_REVIEW, F.PROCEDURE_CONDITIONS_CLAUSE},
    "diagnosis-denial-wrong": {F.CLINICAL_SUPPORT_NEEDS_REVIEW, F.PROCEDURE_CONDITIONS_CLAUSE},
    "knee-mri-findings": {F.CLINICAL_SUPPORT_NEEDS_REVIEW, F.PROCEDURE_CONDITIONS_CLAUSE},
    "knee-mri-undated": {F.CLINICAL_SUPPORT_NEEDS_REVIEW, F.PROCEDURE_CONDITIONS_CLAUSE},
    "knee-mri-late-addendum": {F.CLINICAL_SUPPORT_NEEDS_REVIEW, F.PROCEDURE_CONDITIONS_CLAUSE},
    "lumbar-mri-equivocal": {F.CLINICAL_SUPPORT_NEEDS_REVIEW, F.PROCEDURE_CONDITIONS_CLAUSE},
    "cosmetic-removal": {F.CLINICAL_SUPPORT_NEEDS_REVIEW, F.PROCEDURE_CONDITIONS_CLAUSE},
    "hyaluronan-met": {F.PROCEDURE_CONDITIONS_CLAUSE},
    "hyaluronan-undated": {F.PROCEDURE_CONDITIONS_CLAUSE},
    "airway-pressure-no-report": {F.PROCEDURE_CONDITIONS_CLAUSE},
    "therapy-progress": {F.PROCEDURE_CONDITIONS_CLAUSE},
}

DEV_CASES = [
    case
    for case in build_cases()
    if case.split is EvalSplit.DEV and case.expected.action is not None
]


def scenario_family(case: EvalCase) -> str:
    return case.scenario.rsplit("-", 1)[0]


def test_every_development_scenario_has_an_expectation() -> None:
    assert {scenario_family(case) for case in DEV_CASES} == set(EXPECTED_BY_SCENARIO)


@pytest.mark.parametrize("case", DEV_CASES, ids=lambda case: f"{case.case_id}-{case.scenario}")
async def test_rules_find_exactly_the_expected_facts(
    engine: IRulesEngineService, case: EvalCase
) -> None:
    found = await engine.evaluate(case.case_input(), case.as_of_date)

    assert codes(found) == EXPECTED_BY_SCENARIO[scenario_family(case)]


@pytest.mark.parametrize("case", DEV_CASES, ids=lambda case: case.case_id)
async def test_findings_cite_only_clauses_of_the_case_payer(
    engine: IRulesEngineService, case: EvalCase
) -> None:
    payer_id = case.input["claim"]["payer_id"]

    for finding in await engine.evaluate(case.case_input(), case.as_of_date):
        assert all(clause_id.startswith(f"{payer_id}-") for clause_id in finding.clause_ids)


@pytest.mark.parametrize("payer_id", sorted(RULES))
async def test_generator_limits_agree_with_the_payer_rule_file(payer_id: str) -> None:
    container = Container()
    container.settings.override(providers.Object(Settings(_env_file=None)))
    payer = await container.repositories.policy_repository().get_payer(payer_id)
    generator = RULES[payer_id]

    assert payer is not None
    assert payer.rules.filing_limit_days == generator.filing_limit_days
    assert payer.rules.corrected_claim_days == generator.corrected_claim_days
    assert payer.name == generator.name


# --- Correction route ---------------------------------------------------------


def medicare_sample(sample_id: str) -> tuple[CaseInput, date]:
    raw = json.loads(Path(f"seeders/samples/{sample_id}.json").read_text(encoding="utf-8"))
    return CaseInput.model_validate(raw["input"]), date.fromisoformat(raw["as_of_date"])


async def test_a_correctable_error_brings_in_the_payers_correction_route(
    engine: IRulesEngineService,
) -> None:
    case_input, as_of = medicare_sample("visit-without-modifier-25")

    findings = await engine.evaluate(case_input, as_of)

    route = [finding for finding in findings if finding.code is F.CORRECTION_ROUTE_CLAUSE]
    assert len(route) == 1
    assert route[0].clause_ids == ("MEDICARE-APL-2.3",)
    assert route[0].line_numbers == (1,)


async def test_no_route_is_named_when_nothing_needs_correcting(
    engine: IRulesEngineService,
) -> None:
    for sample_id in ("bone-density-repeat-on-steroids", "claim-filed-after-one-year"):
        case_input, as_of = medicare_sample(sample_id)

        assert F.CORRECTION_ROUTE_CLAUSE not in codes(await engine.evaluate(case_input, as_of))


async def test_no_route_is_named_for_a_payer_whose_rules_have_none(
    engine: IRulesEngineService,
) -> None:
    case = base_case()
    case["claim"]["lines"][0]["modifiers"] = []  # a side modifier is now missing

    findings = await engine.evaluate(CaseInput.model_validate(case), AS_OF)

    assert F.SIDE_MODIFIER_MISSING in codes(findings)
    assert F.CORRECTION_ROUTE_CLAUSE not in codes(findings)
