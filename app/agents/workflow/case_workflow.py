from datetime import date
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from app.agents.routing.after_verification import route_after_verification
from app.agents.states.case_state import CaseState
from app.constants.agents import (
    STEP_APPROVAL,
    STEP_DOCUMENT_RETRIEVAL,
    STEP_INTAKE,
    STEP_RECORD_CHECKS,
    STEP_RETRIEVAL,
    STEP_REVIEW,
    STEP_RULES,
    STEP_TRIAGE,
    STEP_VERIFIER,
    STEP_WRITER,
)
from app.core.exceptions import ConflictError, NotFoundError
from app.interfaces.agents.case_node import ICaseNode
from app.interfaces.agents.case_workflow import ICaseWorkflow
from app.interfaces.service.case_projection_service import ICaseProjectionService
from app.schemas.case_input import CaseInput
from app.schemas.human_decision import HumanDecision


class CaseWorkflow(ICaseWorkflow):
    """The case graph, from the rules to the human gate.

        rules -> retrieval -> intake -> document_retrieval -> triage -> writer -> verifier
                                                                          ^           |
                                                                          +-- failed -+
        verifier, when passed or out of rewrites -> review -> approval

    Each case is one thread in the checkpointer, keyed by its case ID, so a paused case
    survives a restart and finished steps are not run again.
    """

    def __init__(
        self,
        rules_node: ICaseNode,
        retrieval_node: ICaseNode,
        intake_node: ICaseNode,
        record_check_node: ICaseNode,
        document_retrieval_node: ICaseNode,
        triage_node: ICaseNode,
        writer_node: ICaseNode,
        verifier_node: ICaseNode,
        review_node: ICaseNode,
        approval_node: ICaseNode,
        checkpointer: BaseCheckpointSaver[Any],
        projection: ICaseProjectionService,
    ) -> None:
        self._projection = projection
        graph = StateGraph(CaseState)
        steps = (
            (STEP_RULES, rules_node),
            (STEP_RETRIEVAL, retrieval_node),
            (STEP_INTAKE, intake_node),
            (STEP_RECORD_CHECKS, record_check_node),
            (STEP_DOCUMENT_RETRIEVAL, document_retrieval_node),
            (STEP_TRIAGE, triage_node),
            (STEP_WRITER, writer_node),
            (STEP_VERIFIER, verifier_node),
            (STEP_REVIEW, review_node),
            (STEP_APPROVAL, approval_node),
        )
        for name, node in steps:
            graph.add_node(name, node.run)

        graph.add_edge(START, STEP_RULES)
        graph.add_edge(STEP_RULES, STEP_RETRIEVAL)
        graph.add_edge(STEP_RETRIEVAL, STEP_INTAKE)
        graph.add_edge(STEP_INTAKE, STEP_RECORD_CHECKS)
        graph.add_edge(STEP_RECORD_CHECKS, STEP_DOCUMENT_RETRIEVAL)
        graph.add_edge(STEP_DOCUMENT_RETRIEVAL, STEP_TRIAGE)
        graph.add_edge(STEP_TRIAGE, STEP_WRITER)
        graph.add_edge(STEP_WRITER, STEP_VERIFIER)
        graph.add_conditional_edges(
            STEP_VERIFIER,
            route_after_verification,
            {STEP_WRITER: STEP_WRITER, STEP_REVIEW: STEP_REVIEW},
        )
        graph.add_edge(STEP_REVIEW, STEP_APPROVAL)
        graph.add_edge(STEP_APPROVAL, END)
        self._graph = graph.compile(checkpointer=checkpointer)

    async def start(self, case_id: str, case_input: CaseInput, as_of: date) -> CaseState:
        if await self.get(case_id) is not None:
            raise ConflictError(f"Case {case_id} has already been started.")
        await self._run(case_id, CaseState(case_id=case_id, as_of=as_of, case_input=case_input))
        return await self._require(case_id)

    async def resume(self, case_id: str, decision: HumanDecision) -> CaseState:
        snapshot = await self._graph.aget_state(self._thread(case_id))
        if not snapshot.values:
            raise NotFoundError(f"Case {case_id} does not exist.")
        if STEP_APPROVAL not in snapshot.next:
            raise ConflictError(f"Case {case_id} is not waiting for a decision.")
        await self._run(case_id, Command(resume=decision.model_dump(mode="json")))
        return await self._require(case_id)

    async def continue_run(self, case_id: str) -> CaseState:
        snapshot = await self._graph.aget_state(self._thread(case_id))
        if not snapshot.values:
            raise NotFoundError(f"Case {case_id} has no saved state to continue from.")
        if not snapshot.next or STEP_APPROVAL in snapshot.next:
            raise ConflictError(f"Case {case_id} has no unfinished step to continue.")
        # No new input: the graph picks up at the step that did not complete.
        await self._run(case_id, None)
        return await self._require(case_id)

    async def get(self, case_id: str) -> CaseState | None:
        snapshot = await self._graph.aget_state(self._thread(case_id))
        if not snapshot.values:
            return None
        return CaseState.model_validate(snapshot.values)

    async def _run(self, case_id: str, graph_input: Any) -> None:
        """Run until the graph stops, recording the case after every step."""
        async for values in self._graph.astream(
            graph_input, self._thread(case_id), stream_mode="values"
        ):
            # The engine adds its own bookkeeping keys, which are not part of the state.
            state = {key: value for key, value in values.items() if not key.startswith("__")}
            await self._projection.record(CaseState.model_validate(state))

    async def _require(self, case_id: str) -> CaseState:
        state = await self.get(case_id)
        if state is None:
            raise NotFoundError(f"Case {case_id} does not exist.")
        return state

    @staticmethod
    def _thread(case_id: str) -> Any:
        return {"configurable": {"thread_id": case_id}}
