from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.schemas.case_input import CaseInput
from app.schemas.finding import Finding
from app.schemas.note_fact import NoteFact


class IRecordCheck(ABC):
    """One deterministic check on the extracted facts. It reports facts and decides nothing.

    It is given only facts whose quotes were found in their documents, so it never acts
    on words a model wrote.
    """

    @abstractmethod
    def check(self, case_input: CaseInput, facts: Sequence[NoteFact]) -> tuple[Finding, ...]:
        """The findings this check establishes; empty when it has nothing to report."""
