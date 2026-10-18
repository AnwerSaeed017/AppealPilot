from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.schemas.case_clause import CaseClause
from app.schemas.case_input import CaseInput
from app.schemas.draft import Draft
from app.schemas.verification_report import VerificationReport


class ICitationCheckService(ABC):
    @abstractmethod
    def check(
        self, draft: Draft, case_input: CaseInput, clauses: Sequence[CaseClause]
    ) -> VerificationReport:
        """Check by code that each citation's source exists, was selected for this case,
        and contains the words quoted. No model is involved."""
