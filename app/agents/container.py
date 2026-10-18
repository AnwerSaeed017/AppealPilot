from typing import Any

from dependency_injector import containers, providers
from langgraph.checkpoint.base import BaseCheckpointSaver

from app.agents.nodes.approval_node import ApprovalNode
from app.agents.nodes.document_retrieval_node import DocumentRetrievalNode
from app.agents.nodes.intake_node import IntakeNode
from app.agents.nodes.record_check_node import RecordCheckNode
from app.agents.nodes.retrieval_node import RetrievalNode
from app.agents.nodes.review_node import ReviewNode
from app.agents.nodes.rules_node import RulesNode
from app.agents.nodes.triage_node import TriageNode
from app.agents.nodes.verifier_node import VerifierNode
from app.agents.nodes.writer_node import WriterNode
from app.agents.workflow.case_workflow import CaseWorkflow


class AgentContainer(containers.DeclarativeContainer):
    """The case workflow and its nodes."""

    services = providers.DependenciesContainer()
    utilities = providers.DependenciesContainer()
    # Where the state of every case is saved. It comes from the checkpoint store, which
    # has no in-memory default, so a case can never be held only in memory by accident.
    checkpointer: providers.Dependency[BaseCheckpointSaver[Any]] = providers.Dependency(
        instance_of=BaseCheckpointSaver
    )

    rules_node = providers.Factory(
        RulesNode, rules_engine_service=services.rules_engine_service, clock=utilities.clock
    )
    retrieval_node = providers.Factory(
        RetrievalNode,
        case_retrieval_service=services.case_retrieval_service,
        clock=utilities.clock,
    )
    intake_node = providers.Factory(
        IntakeNode, intake_agent_service=services.intake_agent_service, clock=utilities.clock
    )
    record_check_node = providers.Factory(
        RecordCheckNode,
        record_check_service=services.record_check_service,
        clock=utilities.clock,
    )
    document_retrieval_node = providers.Factory(
        DocumentRetrievalNode,
        case_retrieval_service=services.case_retrieval_service,
        clock=utilities.clock,
    )
    triage_node = providers.Factory(
        TriageNode, triage_agent_service=services.triage_agent_service, clock=utilities.clock
    )
    writer_node = providers.Factory(
        WriterNode, writer_agent_service=services.writer_agent_service, clock=utilities.clock
    )
    verifier_node = providers.Factory(
        VerifierNode, verifier_service=services.verifier_service, clock=utilities.clock
    )
    review_node = providers.Factory(ReviewNode, clock=utilities.clock)
    approval_node = providers.Factory(ApprovalNode, clock=utilities.clock)

    # One compiled graph per process.
    case_workflow = providers.Singleton(
        CaseWorkflow,
        rules_node=rules_node,
        retrieval_node=retrieval_node,
        intake_node=intake_node,
        record_check_node=record_check_node,
        document_retrieval_node=document_retrieval_node,
        triage_node=triage_node,
        writer_node=writer_node,
        verifier_node=verifier_node,
        review_node=review_node,
        approval_node=approval_node,
        checkpointer=checkpointer,
        projection=services.case_projection_service,
    )
