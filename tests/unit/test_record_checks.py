from pathlib import Path
from typing import Any

from app.interfaces.repository.policy_repository import IPolicyRepository
from app.repositories.file_policy_repository import FilePolicyRepository
from app.schemas.audit_event import AgentResult, LlmCallRecord
from app.schemas.case_input import CaseInput
from app.schemas.finding import Finding, FindingCode
from app.schemas.note_fact import NoteFact
from app.schemas.payer import Payer
from app.schemas.policy_clause import PolicyClause
from app.schemas.recommended_action import RecommendedAction
from app.schemas.triage_decision import TriageDecision
from app.services.agents.triage_agent_service import TriageAgentService
from app.services.record_check_service import RecordCheckService
from app.services.record_checks.laterality_check import LateralityCheck
from app.services.record_checks.patient_age_check import PatientAgeCheck
from app.services.triage_guards.escalation_finding_guard import EscalationFindingGuard
from app.services.triage_guards.payer_error_guard import PayerErrorGuard
from app.services.triage_guards.visit_documentation_guard import VisitDocumentationGuard
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


class TessalyRules(IPolicyRepository):
    """Answers for any payer with Tessaly's rule set, read from the policy files."""

    def __init__(self) -> None:
        self._files = FilePolicyRepository(Path("seeders/policies"))

    async def get_payer(self, payer_id: str) -> Payer | None:
        return await self._files.get_payer("TESS")

    async def list_clauses(self, payer_id: str) -> tuple[PolicyClause, ...]:
        return await self._files.list_clauses("TESS")

    async def get_clause(self, clause_id: str) -> PolicyClause | None:
        return await self._files.get_clause(clause_id)


def service() -> RecordCheckService:
    return RecordCheckService(
        [LateralityCheck(), PatientAgeCheck()], QuoteMatcher(), TessalyRules()
    )


def codes(findings: tuple[Finding, ...]) -> set[FindingCode]:
    return {finding.code for finding in findings}


NOTE = (
    "Patient: 65-year-old woman.\n"
    "Chief complaint: left knee pain.\n"
    "Procedure: right knee injected with corticosteroid."
)


async def test_a_record_naming_both_sides_is_a_contradiction() -> None:
    case = case_with_note(NOTE)
    facts = [fact("Chief complaint: left knee pain.", 2), fact("Procedure: right knee injected", 3)]

    findings = await service().check(case, facts, ())

    assert codes(findings) == {FindingCode.LATERALITY_CONTRADICTION}
    assert "left: NOTE line 2" in findings[0].message
    assert "right: NOTE line 3" in findings[0].message


async def test_a_record_that_agrees_with_itself_is_not_a_contradiction() -> None:
    # The record says right throughout. If the claim was billed for the left side, that is
    # a billing error to correct, not a contradiction in the record.
    text = "Chief complaint: right knee pain.\nProcedure: right knee injected."
    case = case_with_note(text)

    findings = await service().check(
        case, [fact("right knee pain"), fact("right knee injected")], ()
    )

    assert findings == ()


async def test_a_stated_age_the_claims_patient_could_not_have_is_a_mismatch() -> None:
    case = case_with_note("Patient: 7-year-old boy, new patient.\nAssessment: otitis media.")

    findings = await service().check(case, [fact("Patient: 7-year-old boy, new patient.")], ())

    assert codes(findings) == {FindingCode.DOCUMENT_PATIENT_MISMATCH}
    assert "makes the patient 65" in findings[0].message


async def test_an_age_within_a_year_of_the_claims_is_the_same_patient() -> None:
    case = case_with_note("Patient: 64-year-old woman.")

    assert await service().check(case, [fact("Patient: 64-year-old woman.")], ()) == ()


async def test_a_fact_whose_quote_is_not_in_its_document_is_ignored() -> None:
    # A model wrote "left" into a quote the note does not contain; nothing may follow from it.
    case = case_with_note("Procedure: right knee injected.")

    findings = await service().check(
        case, [fact("right knee injected"), fact("left knee pain")], ()
    )

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
    triage = TriageAgentService(
        FixedTriage(action),  # type: ignore[arg-type]
        CaseRenderer(),
        [EscalationFindingGuard(), VisitDocumentationGuard(), PayerErrorGuard()],
    )
    case = CaseInput.model_validate(case_input_payload())
    result = await triage.decide(case, case.visit_note.encounter_date, findings, [], [])
    return result.output


async def test_a_record_contradiction_escalates_whatever_the_model_chose() -> None:
    decision = await decide(RecommendedAction.CORRECT_AND_RESUBMIT, [CONTRADICTION])

    assert decision.action is RecommendedAction.ESCALATE_TO_HUMAN
    assert decision.reasons[0].startswith("Escalated by code: LATERALITY_CONTRADICTION")
    assert "model reason" in decision.reasons


async def test_a_late_entry_escalates_whatever_the_model_chose() -> None:
    late = Finding(
        code=FindingCode.LATE_ENTRY_AFTER_DENIAL, message="An addendum follows the denial."
    )

    decision = await decide(RecommendedAction.REQUEST_DOCUMENTATION, [late])

    assert decision.action is RecommendedAction.ESCALATE_TO_HUMAN
    assert decision.reasons[0].startswith("Escalated by code: LATE_ENTRY_AFTER_DENIAL")


async def test_without_a_blocking_finding_the_models_choice_stands() -> None:
    decision = await decide(RecommendedAction.CORRECT_AND_RESUBMIT, [])

    assert decision.action is RecommendedAction.CORRECT_AND_RESUBMIT
    assert decision.reasons == ("model reason",)


def finding(code: FindingCode) -> Finding:
    return Finding(code=code, message=f"{code.value} found.")


async def test_a_documentation_request_for_modifier_25_goes_to_a_person() -> None:
    decision = await decide(
        RecommendedAction.REQUEST_DOCUMENTATION, [finding(FindingCode.VISIT_WITHOUT_MODIFIER_25)]
    )

    assert decision.action is RecommendedAction.ESCALATE_TO_HUMAN
    assert decision.reasons[0].startswith("Escalated by code: support for modifier 25")
    assert "model reason" in decision.reasons


async def test_other_choices_on_a_modifier_25_case_stand() -> None:
    for action in (RecommendedAction.CORRECT_AND_RESUBMIT, RecommendedAction.NO_ACTION):
        decision = await decide(action, [finding(FindingCode.VISIT_WITHOUT_MODIFIER_25)])

        assert decision.action is action


async def test_a_correction_of_a_claim_denied_in_error_becomes_an_appeal() -> None:
    decision = await decide(
        RecommendedAction.CORRECT_AND_RESUBMIT, [finding(FindingCode.AUTHORIZATION_NOT_REQUIRED)]
    )

    assert decision.action is RecommendedAction.APPEAL_WITH_EVIDENCE
    assert decision.reasons[0].startswith("Changed by code: AUTHORIZATION_NOT_REQUIRED")


async def test_a_correction_stands_when_the_claim_also_has_an_error_to_correct() -> None:
    decision = await decide(
        RecommendedAction.CORRECT_AND_RESUBMIT,
        [finding(FindingCode.FILED_WITHIN_LIMIT), finding(FindingCode.SIDE_MODIFIER_MISSING)],
    )

    assert decision.action is RecommendedAction.CORRECT_AND_RESUBMIT


async def test_escalation_findings_take_priority_over_other_guards() -> None:
    decision = await decide(
        RecommendedAction.CORRECT_AND_RESUBMIT,
        [finding(FindingCode.AUTHORIZATION_NOT_REQUIRED), CONTRADICTION],
    )

    assert decision.action is RecommendedAction.ESCALATE_TO_HUMAN
