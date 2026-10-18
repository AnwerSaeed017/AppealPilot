from abc import ABC, abstractmethod

from app.schemas.audit_event import AgentResult
from app.schemas.case_input import CaseInput
from app.schemas.note_fact import NoteFacts


class IIntakeAgentService(ABC):
    @abstractmethod
    async def extract(self, case_input: CaseInput) -> AgentResult[NoteFacts]:
        """The facts stated in the visit note and supporting documents, each with the
        line and the exact words it comes from."""
