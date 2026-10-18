from collections.abc import Sequence
from datetime import date

from app.core.exceptions import ValidationFailedError
from app.interfaces.repository.policy_repository import IPolicyRepository
from app.interfaces.service.finding_rule import IFindingRule
from app.interfaces.service.rule import IRule
from app.interfaces.service.rules_engine_service import IRulesEngineService
from app.schemas.case_input import CaseInput
from app.schemas.finding import Finding
from app.schemas.rule_context import RuleContext


class RulesEngineService(IRulesEngineService):
    """Runs every registered rule against a case. No model is involved.

    The rules run first and independently; the finding rules then run over what they
    found.
    """

    def __init__(
        self,
        policy_repository: IPolicyRepository,
        rules: Sequence[IRule],
        finding_rules: Sequence[IFindingRule] = (),
    ) -> None:
        self._policy_repository = policy_repository
        self._rules = tuple(rules)
        self._finding_rules = tuple(finding_rules)

    async def evaluate(self, case_input: CaseInput, as_of: date) -> tuple[Finding, ...]:
        payer = await self._policy_repository.get_payer(case_input.claim.payer_id)
        if payer is None:
            raise ValidationFailedError(f"Unknown payer {case_input.claim.payer_id}.")

        context = RuleContext(case_input=case_input, payer_rules=payer.rules, as_of=as_of)
        findings = tuple(finding for rule in self._rules for finding in rule.check(context))
        added = tuple(
            finding for rule in self._finding_rules for finding in rule.check(context, findings)
        )
        return findings + added
