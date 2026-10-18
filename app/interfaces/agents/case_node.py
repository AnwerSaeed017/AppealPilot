from abc import ABC, abstractmethod
from typing import Any

from app.agents.states.case_state import CaseState


class ICaseNode(ABC):
    """One step of the case workflow.

    A node holds no logic of its own: it reads the state, calls one service, and
    returns the fields that changed together with an audit event.
    """

    @abstractmethod
    async def run(self, state: CaseState) -> dict[str, Any]:
        """The state fields this step changes."""
