from abc import ABC, abstractmethod

from app.schemas.finding import Finding
from app.schemas.rule_context import RuleContext


class IRule(ABC):
    """One deterministic check. It reports facts and decides nothing."""

    @abstractmethod
    def check(self, context: RuleContext) -> tuple[Finding, ...]:
        """The findings this rule establishes; empty when it has nothing to report."""
