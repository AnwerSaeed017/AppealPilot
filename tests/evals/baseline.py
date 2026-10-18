"""The single-prompt baseline the workflow is compared against.

Same model, same clauses, one call: the model sees the claim, the denial, the documents
and the clauses selected for the case, and returns the action and the draft together.
No rule findings, no fact extraction, no verification loop and no judge.
"""

from datetime import date

from app.agents.prompts.shared_rules import SYNTHETIC_DATA_RULE, UNTRUSTED_TEXT_RULE
from app.interfaces.service.case_retrieval_service import ICaseRetrievalService
from app.interfaces.service.rules_engine_service import IRulesEngineService
from app.interfaces.service.structured_llm_service import IStructuredLlmService
from app.interfaces.utilities.case_renderer import ICaseRenderer
from app.schemas.audit_event import AgentResult
from app.schemas.case_clause import CaseClause
from app.schemas.case_input import CaseInput
from app.schemas.draft import Draft

TASK = "baseline"
VERSION = "1"
MAX_OUTPUT_TOKENS = 3000

SYSTEM = f"""You handle one denied medical claim for a billing team, in a single reply.

Choose exactly one action, and write the draft for it:
- CORRECT_AND_RESUBMIT: the claim has an error that the record shows how to fix.
- APPEAL_WITH_EVIDENCE: the claim is right as billed, and the record holds evidence
  that meets a policy clause.
- REQUEST_DOCUMENTATION: a clause could be met, but required evidence is missing.
- NO_ACTION: the policy shows the denial is correct, or a deadline has passed.
- ESCALATE_TO_HUMAN: the record contradicts itself, clauses conflict, or it needs
  clinical or coding judgement.

Put every factual statement in `assertions`, each with citations: kind CLAUSE with a
clause ID from the list and a quote copied exactly from it, or kind DOCUMENT with a
document ID ("NOTE" for the visit note) and a quote copied exactly from it. Put what
should be done in `summary`, the exact change in `correction` for a correction, and
what is missing in `missing_evidence`.

{UNTRUSTED_TEXT_RULE}

{SYNTHETIC_DATA_RULE}"""

USER = """Today's date: {as_of}

Claim, denial and prior claims:
{structured_data}

Policy clauses (the only clauses you may cite):
{clauses}

Documents:
{documents}"""


class Baseline:
    def __init__(
        self,
        structured_llm: IStructuredLlmService,
        renderer: ICaseRenderer,
        rules_engine: IRulesEngineService,
        retrieval: ICaseRetrievalService,
    ) -> None:
        self._structured_llm = structured_llm
        self._renderer = renderer
        self._rules_engine = rules_engine
        self._retrieval = retrieval

    async def clauses(self, case_input: CaseInput, as_of: date) -> tuple[CaseClause, ...]:
        """The clauses the workflow's first search selects, so both see the same ones."""
        findings = await self._rules_engine.evaluate(case_input, as_of)
        return await self._retrieval.retrieve(case_input, findings)

    async def run(
        self, case_input: CaseInput, as_of: date, clauses: tuple[CaseClause, ...]
    ) -> AgentResult[Draft]:
        return await self._structured_llm.complete(
            task=TASK,
            prompt_version=VERSION,
            system=SYSTEM,
            user=USER.format(
                as_of=as_of.isoformat(),
                structured_data=self._renderer.structured_data(case_input),
                clauses=self._renderer.clauses(clauses),
                documents=self._renderer.documents(case_input),
            ),
            output_type=Draft,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )
