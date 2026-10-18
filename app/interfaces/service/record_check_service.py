from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.schemas.case_input import CaseInput
from app.schemas.finding import Finding
from app.schemas.note_fact import NoteFact


class IRecordCheckService(ABC):
    @abstractmethod
    def check(self, case_input: CaseInput, facts: Sequence[NoteFact]) -> tuple[Finding, ...]:
        """Run every record check on the facts whose quotes are found in their documents."""
