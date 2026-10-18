from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import date

from app.schemas.audit_event import AgentResult
from app.schemas.case_clause import CaseClause
from app.schemas.case_input import CaseInput
from app.schemas.finding import Finding
from app.schemas.note_fact import NoteFact
from app.schemas.triage_decision import TriageDecision


class ITriageAgentService(ABC):
    @abstractmethod
    async def decide(
        self,
        case_input: CaseInput,
        as_of: date,
        findings: Sequence[Finding],
        clauses: Sequence[CaseClause],
        note_facts: Sequence[NoteFact],
    ) -> AgentResult[TriageDecision]:
        """Choose one of the five actions for the case, with reasons and a confidence."""
