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
        findings: Sequence[Finding],
    ) -> tuple[CaseClause, ...]:
        """The clauses already selected, plus those the record made relevant.

        First appends any clause a finding cites that is not yet selected: findings made
        after the record was read can cite clauses the first search had no reason to
        find. Then searches the payer's clauses with the facts extracted from the
        supporting documents and appends the best new matches.
        """
