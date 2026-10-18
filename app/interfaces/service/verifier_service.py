from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.schemas.case_clause import CaseClause
from app.schemas.case_input import CaseInput
from app.schemas.draft import Draft
from app.schemas.verification_report import Verification


class IVerifierService(ABC):
    @abstractmethod
    async def verify(
        self, draft: Draft, case_input: CaseInput, clauses: Sequence[CaseClause]
    ) -> Verification:
        """Check every assertion of the draft against the sources it cites."""
