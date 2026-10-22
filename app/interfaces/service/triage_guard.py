from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.schemas.finding import Finding
from app.schemas.triage_decision import TriageDecision


class ITriageGuard(ABC):
    """A check by code on the action the model chose, against what code established.

    It returns a replacement decision when the model's choice contradicts a finding, and
    None when the choice stands. A replacement keeps the model's own choice and reasons
    after the code's, so a reviewer sees both.
    """

    @abstractmethod
    def check(self, findings: Sequence[Finding], decision: TriageDecision) -> TriageDecision | None:
        """The decision code requires instead, or None when the model's choice stands."""
