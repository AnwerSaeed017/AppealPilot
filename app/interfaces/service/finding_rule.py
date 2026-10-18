from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.schemas.finding import Finding
from app.schemas.rule_context import RuleContext


class IFindingRule(ABC):
    """A deterministic check that runs after the other rules and reads their findings.

    Like every rule it reports facts and decides nothing.
    """

    @abstractmethod
    def check(self, context: RuleContext, findings: Sequence[Finding]) -> tuple[Finding, ...]:
        """The findings this rule adds; empty when it has nothing to report."""
