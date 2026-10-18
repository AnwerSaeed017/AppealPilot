from typing import Any

from app.agents.states.case_state import CaseState
from app.constants.agents import STEP_RULES
from app.interfaces.agents.case_node import ICaseNode
from app.interfaces.service.rules_engine_service import IRulesEngineService
from app.interfaces.utilities.clock import IClock
from app.schemas.audit_event import AuditEvent


class RulesNode(ICaseNode):
    """Runs the deterministic rules. No model is called."""

    def __init__(self, rules_engine_service: IRulesEngineService, clock: IClock) -> None:
        self._rules_engine_service = rules_engine_service
        self._clock = clock

    async def run(self, state: CaseState) -> dict[str, Any]:
        findings = await self._rules_engine_service.evaluate(state.case_input, state.as_of)
        codes = ", ".join(finding.code.value for finding in findings) or "none"
        return {
            "findings": findings,
            "audit": (
                AuditEvent(
                    step=STEP_RULES, at=self._clock.now(), summary=f"Rule findings: {codes}."
                ),
            ),
        }
