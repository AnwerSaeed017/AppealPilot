from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.schemas.case_clause import CaseClause
from app.schemas.case_input import CaseInput
from app.schemas.finding import Finding
from app.schemas.note_fact import NoteFact


class ICaseRenderer(ABC):
    """Turns parts of a case into the text a model is shown."""

    @abstractmethod
    def structured_data(self, case_input: CaseInput) -> str:
        """The claim, the denial and any prior claims, as JSON."""

    @abstractmethod
    def documents(self, case_input: CaseInput) -> str:
        """The visit note and supporting documents, delimited, every line numbered."""

    @abstractmethod
    def findings(self, findings: Sequence[Finding]) -> str:
        """The rule findings, one per line."""

    @abstractmethod
    def clauses(self, clauses: Sequence[CaseClause]) -> str:
        """The selected policy clauses, each under its clause ID."""

    @abstractmethod
    def note_facts(self, note_facts: Sequence[NoteFact]) -> str:
        """The extracted facts, each with its source line and quote."""

    @abstractmethod
    def without_line_numbers(self, quote: str) -> str:
        """A quote with any line numbers this renderer added to the documents removed.

        The numbers are not part of the source; a model sometimes copies them.
        """

    @abstractmethod
    def fact_pointers(self, note_facts: Sequence[NoteFact]) -> str:
        """The extracted facts, each with its source document and line but not its quote.

        For a reader that is also shown the documents, so the quote would only repeat
        text it already has.
        """
