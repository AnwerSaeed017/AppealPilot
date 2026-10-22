from abc import ABC, abstractmethod

from app.schemas.finding import Finding
from app.schemas.record_check_context import RecordCheckContext


class IRecordCheck(ABC):
    """One deterministic check on the record once it has been read. It reports facts and
    decides nothing.

    It is given only facts whose quotes were found in their documents, so it never acts
    on words a model wrote.
    """

    @abstractmethod
    def check(self, context: RecordCheckContext) -> tuple[Finding, ...]:
        """The findings this check establishes; empty when it has nothing to report."""
