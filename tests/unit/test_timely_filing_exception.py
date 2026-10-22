"""The timely filing exception check: by hand on small cases, and across the development
cases, where it must fire on exactly the scenarios whose label rests on an exception.

Only the development cases are used here. The locked cases are for release runs.
"""

from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pytest
from dependency_injector import providers

from app.containers.container import Container
from app.core.settings import Settings
from app.interfaces.service.record_check_service import IRecordCheckService
from app.interfaces.service.rules_engine_service import IRulesEngineService
from app.repositories.file_policy_repository import FilePolicyRepository
from app.schemas.case_input import CaseInput
from app.schemas.eval_case import EvalCase, EvalSplit
from app.schemas.finding import Finding, FindingCode
from app.schemas.payer_rule_set import PayerRuleSet
from app.schemas.record_check_context import RecordCheckContext
from app.services.record_checks.timely_filing_exception_check import TimelyFilingExceptionCheck
from tests.evals.generator.build import build_cases

SERVICE = date(2026, 1, 10)
# Tessaly: 180 days to file, 90 more after a primary payer's statement.
RECEIVED = SERVICE + timedelta(days=200)
LATE = Finding(code=FindingCode.FILING_LIMIT_EXCEEDED, message="Filed 200 days after.")


async def tessaly_rules() -> PayerRuleSet:
    payer = await FilePolicyRepository(Path("seeders/policies")).get_payer("TESS")
    assert payer is not None
    return payer.rules


def case_with(*documents: dict[str, Any]) -> CaseInput:
    return CaseInput.model_validate(
        {
            "claim": {
                "claim_id": "CLM-1",
                "payer_id": "TESS",
                "member_id": "TESS-1",
                "patient_id": "PT-1",
                "patient_date_of_birth": "1960-01-01",
                "billing_provider_npi": "1234567893",
                "place_of_service": "11",
                "submitted_date": RECEIVED.isoformat(),
                "diagnosis_codes": ["I10"],
                "lines": [
                    {
                        "line_number": 1,
                        "service_date": SERVICE.isoformat(),
                        "procedure_code": "99213",
                        "modifiers": [],
                        "diagnosis_pointers": [1],
                        "units": 1,
                        "charge_amount": "135.00",
                    }
                ],
                "total_charge": "135.00",
            },
            "denial": {
                "claim_id": "CLM-1",
                "payer_id": "TESS",
                "group_code": "CO",
                "carc_code": "29",
                "denial_date": (RECEIVED + timedelta(days=15)).isoformat(),
                "denied_amount": "135.00",
            },
            "visit_note": {
                "encounter_date": SERVICE.isoformat(),
                "text": "Visit for hypertension.",
            },
            "supporting_documents": list(documents),
        }
    )


def document(document_id: str, kind: str, on: date, text: str) -> dict[str, Any]:
    return {"document_id": document_id, "kind": kind, "document_date": on.isoformat(), "text": text}


async def found(case: CaseInput, findings: tuple[Finding, ...] = (LATE,)) -> tuple[Finding, ...]:
    context = RecordCheckContext(
        case_input=case, payer_rules=await tessaly_rules(), facts=(), findings=findings
    )
    return TimelyFilingExceptionCheck().check(context)


EOB_TEXT = "Explanation of benefits from the primary payer\nPrimary payment made."
REPORT_TEXT = "Clearinghouse claim status report\nAccepted by payer: 2026-01-30\nStatus: Accepted"


@pytest.mark.parametrize(("days_before", "expected"), [(30, 1), (90, 1), (91, 0)])
async def test_a_secondary_claim_is_timely_within_the_days_after_the_primary_statement(
    days_before: int, expected: int
) -> None:
    eob = document("EOB", "PRIMARY_PAYER_EOB", RECEIVED - timedelta(days=days_before), EOB_TEXT)

    result = await found(case_with(eob))

    assert len(result) == expected
    if result:
        assert result[0].code is FindingCode.TIMELY_FILING_EXCEPTION_DOCUMENTED
        assert result[0].clause_ids == ("TESS-TF-2.1",)


async def test_an_acceptance_report_dated_within_the_limit_is_proof() -> None:
    report = document("CLR", "CLEARINGHOUSE_REPORT", SERVICE + timedelta(days=20), REPORT_TEXT)

    result = await found(case_with(report))

    assert [f.clause_ids for f in result] == [("TESS-TF-2.2",)]
    assert "20 days after the service" in result[0].message


@pytest.mark.parametrize(
    ("kind", "days_after", "text"),
    [
        # The provider's own billing system is never proof.
        ("BILLING_NOTE", 20, "Status: Accepted"),
        # Accepted, but only after the limit had passed.
        ("CLEARINGHOUSE_REPORT", 190, REPORT_TEXT),
        # A report that records a rejection proves nothing.
        ("CLEARINGHOUSE_REPORT", 20, "Status: Rejected by payer. Not accepted."),
        # Sent is not accepted.
        ("CLEARINGHOUSE_REPORT", 20, "Claim transmitted. Status: Sent"),
    ],
)
async def test_documents_that_do_not_prove_timely_filing(
    kind: str, days_after: int, text: str
) -> None:
    report = document("DOC", kind, SERVICE + timedelta(days=days_after), text)

    assert await found(case_with(report)) == ()


async def test_nothing_is_reported_when_the_claim_was_not_late() -> None:
    report = document("CLR", "CLEARINGHOUSE_REPORT", SERVICE + timedelta(days=20), REPORT_TEXT)

    assert await found(case_with(report), findings=()) == ()


# --- The development cases ----------------------------------------------------

# Scenario families whose label rests on a filing exception or on proof of timely filing.
EXCEPTION_SCENARIOS = {"filing-accepted", "filing-primary-payer"}
HAND_WRITTEN_EXCEPTIONS = {"secondary-payer-cob-timely-filing"}


def development_cases() -> list[EvalCase]:
    generated = [case for case in build_cases() if case.split is EvalSplit.DEV]
    hand = [
        EvalCase.model_validate_json(path.read_text(encoding="utf-8"))
        for path in sorted(Path("tests/evals/cases/dev").glob("HAND-*.json"))
    ]
    return [case for case in generated + hand if case.expected.action is not None]


@pytest.fixture(scope="module")
def container() -> Container:
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
    return container


@pytest.mark.parametrize("case", development_cases(), ids=lambda case: case.case_id)
async def test_the_check_fires_on_exactly_the_cases_that_rest_on_an_exception(
    container: Container, case: EvalCase
) -> None:
    rules: IRulesEngineService = container.services.rules_engine_service()
    checks: IRecordCheckService = container.services.record_check_service()
    case_input = case.case_input()

    findings = await rules.evaluate(case_input, case.as_of_date)
    added = await checks.check(case_input, (), findings)

    fired = FindingCode.TIMELY_FILING_EXCEPTION_DOCUMENTED in {f.code for f in added}
    family = case.scenario.rsplit("-", 1)[0]
    expected = family in EXCEPTION_SCENARIOS or case.scenario in HAND_WRITTEN_EXCEPTIONS
    assert fired is expected
