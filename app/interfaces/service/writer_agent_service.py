from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.schemas.audit_event import AgentResult
from app.schemas.case_clause import CaseClause
from app.schemas.case_input import CaseInput
from app.schemas.draft import Draft
from app.schemas.finding import Finding
from app.schemas.note_fact import NoteFact
from app.schemas.triage_decision import TriageDecision
from app.schemas.verification_report import VerificationReport


class IWriterAgentService(ABC):
    @abstractmethod
    async def draft(
        self,
        case_input: CaseInput,
        findings: Sequence[Finding],
        clauses: Sequence[CaseClause],
        note_facts: Sequence[NoteFact],
        triage: TriageDecision,
        previous: Draft | None,
        feedback: VerificationReport | None,
    ) -> AgentResult[Draft]:
        """Write the draft for the chosen action, every assertion with its citations.

        `previous` and `feedback` are given when an earlier draft failed verification.
        """
