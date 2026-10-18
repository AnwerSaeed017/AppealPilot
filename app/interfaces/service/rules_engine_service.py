from abc import ABC, abstractmethod
from datetime import date

from app.schemas.case_input import CaseInput
from app.schemas.finding import Finding


class IRulesEngineService(ABC):
    @abstractmethod
    async def evaluate(self, case_input: CaseInput, as_of: date) -> tuple[Finding, ...]:
        """Every finding the rules establish for the case as it stands on `as_of`.

        Raises ValidationFailedError when the claim's payer is not known.
        """
