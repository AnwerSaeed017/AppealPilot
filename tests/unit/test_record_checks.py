from typing import Any

from app.schemas.audit_event import AgentResult, LlmCallRecord
from app.schemas.case_input import CaseInput
from app.schemas.finding import Finding, FindingCode
from app.schemas.note_fact import NoteFact
from app.schemas.recommended_action import RecommendedAction
from app.schemas.triage_decision import TriageDecision
from app.services.agents.triage_agent_service import TriageAgentService
from app.services.record_check_service import RecordCheckService
from app.services.record_checks.laterality_check import LateralityCheck
from app.services.record_checks.patient_age_check import PatientAgeCheck
from app.utilities.case_renderer import CaseRenderer
from app.utilities.quote_matcher import QuoteMatcher
from tests.samples import case_input_payload

# The patient in the sample case was born 1961-03-14 and seen 2026-06-02: aged 65.


def case_with_note(text: str) -> CaseInput:
    payload = case_input_payload()
    payload["visit_note"]["text"] = text
    return CaseInput.model_validate(payload)


def fact(quote: str, line: int = 1) -> NoteFact:
    return NoteFact(statement=quote, document_id="NOTE", line_number=line, quote=quote)


def service() -> RecordCheckService:
    return RecordCheckService([LateralityCheck(), PatientAgeCheck()], QuoteMatcher())


def codes(findings: tuple[Finding, ...]) -> set[FindingCode]:
    return {finding.code for finding in findings}


NOTE = (
    "Patient: 65-year-old woman.\n"
    "Chief complaint: left knee pain.\n"
    "Procedure: right knee injected with corticosteroid."
)


def test_a_record_naming_both_sides_is_a_contradiction() -> None:
    case = case_with_note(NOTE)
    facts = [fact("Chief complaint: left knee pain.", 2), fact("Procedure: right knee injected", 3)]

    findings = service().check(case, facts)

    assert codes(findings) == {FindingCode.LATERALITY_CONTRADICTION}
    assert "left: NOTE line 2" in findings[0].message
    assert "right: NOTE line 3" in findings[0].message


def test_a_record_that_agrees_with_itself_is_not_a_contradiction() -> None:
    # The record says right throughout. If the claim was billed for the left side, that is
    # a billing error to correct, not a contradiction in the record.
    text = "Chief complaint: right knee pain.\nProcedure: right knee injected."
    case = case_with_note(text)

    findings = service().check(case, [fact("right knee pain"), fact("right knee injected")])

    assert findings == ()


def test_a_stated_age_the_claims_patient_could_not_have_is_a_mismatch() -> None:
    case = case_with_note("Patient: 7-year-old boy, new patient.\nAssessment: otitis media.")

    findings = service().check(case, [fact("Patient: 7-year-old boy, new patient.")])

    assert codes(findings) == {FindingCode.DOCUMENT_PATIENT_MISMATCH}
    assert "makes the patient 65" in findings[0].message


def test_an_age_within_a_year_of_the_claims_is_the_same_patient() -> None:
    case = case_with_note("Patient: 64-year-old woman.")

    assert service().check(case, [fact("Patient: 64-year-old woman.")]) == ()


def test_a_fact_whose_quote_is_not_in_its_document_is_ignored() -> None:
    # A model wrote "left" into a quote the note does not contain; nothing may follow from it.
    case = case_with_note("Procedure: right knee injected.")

    findings = service().check(case, [fact("right knee injected"), fact("left knee pain")])

    assert findings == ()


class FixedTriage:
    """Stands in for the structured model call and returns one decision."""

    def __init__(self, action: RecommendedAction) -> None:
        self._action = action

    async def complete(self, **_: Any) -> AgentResult[TriageDecision]:
        return AgentResult(
            output=TriageDecision(action=self._action, confidence=0.9, reasons=("model reason",)),
            llm_call=LlmCallRecord(
                provider="mock",
                model="mock",
                input_tokens=1,
                output_tokens=1,
                latency_ms=1.0,
                cached=False,
                attempts=1,
            ),
        )


CONTRADICTION = Finding(
    code=FindingCode.LATERALITY_CONTRADICTION, message="The record names both sides."
)


async def decide(action: RecommendedAction, findings: list[Finding]) -> TriageDecision:
    triage = TriageAgentService(FixedTriage(action), CaseRenderer())  # type: ignore[arg-type]
    case = CaseInput.model_validate(case_input_payload())
    result = await triage.decide(case, case.visit_note.encounter_date, findings, [], [])
    return result.output


async def test_a_record_contradiction_escalates_whatever_the_model_chose() -> None:
    decision = await decide(RecommendedAction.CORRECT_AND_RESUBMIT, [CONTRADICTION])

    assert decision.action is RecommendedAction.ESCALATE_TO_HUMAN
    assert decision.reasons[0].startswith("Escalated by code: LATERALITY_CONTRADICTION")
    assert "model reason" in decision.reasons


async def test_without_a_blocking_finding_the_models_choice_stands() -> None:
    decision = await decide(RecommendedAction.CORRECT_AND_RESUBMIT, [])

    assert decision.action is RecommendedAction.CORRECT_AND_RESUBMIT
    assert decision.reasons == ("model reason",)
