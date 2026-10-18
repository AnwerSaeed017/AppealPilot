from collections.abc import Sequence

from app.interfaces.service.citation_check_service import ICitationCheckService
from app.interfaces.service.judge_agent_service import IJudgeAgentService
from app.interfaces.service.verifier_service import IVerifierService
from app.schemas.case_clause import CaseClause
from app.schemas.case_input import CaseInput
from app.schemas.draft import Draft
from app.schemas.verification_report import (
    AssertionVerdict,
    Verification,
    VerificationReport,
)

_NO_VERDICT = "the judge gave no verdict for this assertion"


class TwoStageVerifierService(IVerifierService):
    """Verifies a draft in two stages, cheapest first.

    1. Code checks every citation: the source exists, was selected for this case, and
       contains the quoted words.
    2. A model judges whether the quoted words support the assertion. Only assertions
       that passed stage 1 are sent; one that failed has already failed.

    An assertion is supported only if it passes both. Anything the judge leaves out
    counts as unsupported, so a missing verdict can never pass an assertion.
    """

    def __init__(
        self, citation_check_service: ICitationCheckService, judge_agent_service: IJudgeAgentService
    ) -> None:
        self._citation_check_service = citation_check_service
        self._judge_agent_service = judge_agent_service

    async def verify(
        self, draft: Draft, case_input: CaseInput, clauses: Sequence[CaseClause]
    ) -> Verification:
        checked = self._citation_check_service.check(draft, case_input, clauses)
        to_judge = [verdict.assertion_index for verdict in checked.verdicts if verdict.supported]
        if not to_judge:
            return Verification(report=checked)

        judged = await self._judge_agent_service.judge(draft, to_judge, case_input, clauses)
        by_index = {verdict.assertion_index: verdict for verdict in judged.output.verdicts}

        verdicts: list[AssertionVerdict] = []
        for verdict in checked.verdicts:
            if not verdict.supported:
                verdicts.append(verdict)
                continue
            opinion = by_index.get(verdict.assertion_index)
            if opinion is not None and opinion.supported:
                verdicts.append(verdict)
            else:
                reason = opinion.reason if opinion is not None else _NO_VERDICT
                verdicts.append(
                    AssertionVerdict(
                        assertion_index=verdict.assertion_index,
                        supported=False,
                        problems=(f"judge: {reason}",),
                    )
                )
        return Verification(
            report=VerificationReport(verdicts=tuple(verdicts)), llm_call=judged.llm_call
        )
