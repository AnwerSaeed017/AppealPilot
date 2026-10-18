from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.schemas.case_input import CaseInput
from app.schemas.finding import Finding


class ICaseQueryService(ABC):
    @abstractmethod
    def build(self, case_input: CaseInput, findings: Sequence[Finding]) -> str:
        """The text to search the payer's policies with for this case."""
