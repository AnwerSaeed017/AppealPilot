from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.schemas.audit_event import AgentResult
from app.schemas.case_clause import CaseClause
from app.schemas.case_input import CaseInput
from app.schemas.draft import Draft
from app.schemas.verification_report import JudgeVerdicts


class IJudgeAgentService(ABC):
    @abstractmethod
    async def judge(
        self,
        draft: Draft,
        assertion_indexes: Sequence[int],
        case_input: CaseInput,
        clauses: Sequence[CaseClause],
    ) -> AgentResult[JudgeVerdicts]:
        """Decide, for each assertion asked about, whether its quotes support it."""
