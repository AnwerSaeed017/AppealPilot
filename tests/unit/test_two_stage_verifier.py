from collections.abc import Sequence
from typing import Any

from app.interfaces.service.judge_agent_service import IJudgeAgentService
from app.schemas.audit_event import AgentResult, LlmCallRecord
from app.schemas.case_clause import CaseClause, ClauseOrigin
from app.schemas.case_input import CaseInput
from app.schemas.draft import Draft
from app.schemas.policy_clause import PolicyClause
from app.schemas.verification_report import JudgeVerdict, JudgeVerdicts
from app.services.citation_verifier_service import CitationVerifierService
from app.services.two_stage_verifier_service import TwoStageVerifierService
from app.utilities.quote_matcher import QuoteMatcher
from tests.samples import case_input_payload, policy_clause_payload

CASE = CaseInput.model_validate(case_input_payload())
SELECTED = [
    CaseClause(
        clause=PolicyClause.model_validate(policy_clause_payload()),
        rank=1,
        origin=ClauseOrigin.SEARCH,
    )
]
REAL = {"kind": "CLAUSE", "source_id": "ACME-PA-4.2", "quote": "may be reconsidered"}
INVENTED = {"kind": "CLAUSE", "source_id": "ACME-PA-9.9", "quote": "anything"}
CALL = LlmCallRecord(
    provider="judge",
    model="j-1",
    input_tokens=50,
    output_tokens=10,
    latency_ms=5,
    cached=False,
    attempts=1,
)


class FakeJudge(IJudgeAgentService):
    """Answers with the given opinions and records which assertions it was asked about."""

    def __init__(self, opinions: dict[int, bool]) -> None:
        self._opinions = opinions
        self.asked: list[list[int]] = []

    async def judge(
        self,
        draft: Draft,
        assertion_indexes: Sequence[int],
        case_input: CaseInput,
        clauses: Sequence[CaseClause],
    ) -> AgentResult[JudgeVerdicts]:
        self.asked.append(list(assertion_indexes))
        verdicts = tuple(
            JudgeVerdict(assertion_index=index, supported=supported, reason="because")
            for index, supported in self._opinions.items()
        )
        return AgentResult[JudgeVerdicts](output=JudgeVerdicts(verdicts=verdicts), llm_call=CALL)


def draft_of(*citations: dict[str, Any]) -> Draft:
    """A draft with one assertion per citation given."""
    return Draft.model_validate(
        {
            "action": "APPEAL_WITH_EVIDENCE",
            "summary": "Appeal.",
            "assertions": [
                {"text": f"Statement {index}.", "citations": [citation]}
                for index, citation in enumerate(citations)
            ],
        }
    )


def verifier(judge: FakeJudge) -> TwoStageVerifierService:
    return TwoStageVerifierService(CitationVerifierService(QuoteMatcher()), judge)


async def test_an_assertion_passes_only_when_both_stages_pass() -> None:
    judge = FakeJudge({0: True})

    result = await verifier(judge).verify(draft_of(REAL), CASE, SELECTED)

    assert result.report.passed
    assert result.llm_call == CALL


async def test_a_real_quote_the_judge_rejects_fails_with_the_judges_reason() -> None:
    judge = FakeJudge({0: False})

    result = await verifier(judge).verify(draft_of(REAL), CASE, SELECTED)

    assert not result.report.passed
    assert result.report.verdicts[0].problems == ("judge: because",)


async def test_only_assertions_that_passed_the_code_check_go_to_the_judge() -> None:
    judge = FakeJudge({1: True})

    result = await verifier(judge).verify(draft_of(INVENTED, REAL), CASE, SELECTED)

    assert judge.asked == [[1]]
    assert [verdict.supported for verdict in result.report.verdicts] == [False, True]
    assert "was not selected" in result.report.verdicts[0].problems[0]


async def test_the_judge_cannot_rescue_an_assertion_the_code_check_failed() -> None:
    judge = FakeJudge({0: True, 1: True})

    result = await verifier(judge).verify(draft_of(INVENTED, REAL), CASE, SELECTED)

    assert result.report.verdicts[0].supported is False


async def test_an_assertion_the_judge_says_nothing_about_fails() -> None:
    judge = FakeJudge({0: True})  # asked about 0 and 1, answers only for 0

    result = await verifier(judge).verify(draft_of(REAL, REAL), CASE, SELECTED)

    assert [verdict.supported for verdict in result.report.verdicts] == [True, False]
    assert "no verdict" in result.report.verdicts[1].problems[0]


async def test_the_judge_is_not_called_when_nothing_passed_the_code_check() -> None:
    judge = FakeJudge({})

    result = await verifier(judge).verify(draft_of(INVENTED), CASE, SELECTED)

    assert judge.asked == []
    assert result.llm_call is None
    assert not result.report.passed


async def test_a_draft_with_no_assertions_passes_without_a_model_call() -> None:
    judge = FakeJudge({})
    draft = Draft.model_validate({"action": "NO_ACTION", "summary": "Nothing to do."})

    result = await verifier(judge).verify(draft, CASE, SELECTED)

    assert result.report.passed
    assert judge.asked == []
