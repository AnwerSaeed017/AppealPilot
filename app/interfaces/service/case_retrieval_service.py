from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.schemas.case_clause import CaseClause
from app.schemas.case_input import CaseInput
from app.schemas.finding import Finding
from app.schemas.note_fact import NoteFact


class ICaseRetrievalService(ABC):
    @abstractmethod
    async def retrieve(
        self, case_input: CaseInput, findings: Sequence[Finding]
    ) -> tuple[CaseClause, ...]:
        """The clauses of the claim's payer that apply to this case, most relevant first.

        Never returns a clause of another payer, and never more than the configured limit.
        """

    @abstractmethod
    async def extend(
        self,
        case_input: CaseInput,
        clauses: Sequence[CaseClause],
        note_facts: Sequence[NoteFact],
    ) -> tuple[CaseClause, ...]:
        """The clauses already selected, plus a few found from the supporting documents.

        Searches the payer's clauses with the facts extracted from the supporting
        documents and appends the best new matches. Returns the clauses unchanged when
        no fact comes from a supporting document.
        """
