from dependency_injector import containers, providers

from app.constants.agents import MAX_OUTPUT_ATTEMPTS
from app.core.settings import Settings
from app.services.agents.intake_agent_service import IntakeAgentService
from app.services.agents.judge_agent_service import JudgeAgentService
from app.services.agents.triage_agent_service import TriageAgentService
from app.services.agents.writer_agent_service import WriterAgentService
from app.services.bm25_policy_retrieval_service import Bm25PolicyRetrievalService
from app.services.case_projection_service import CaseProjectionService
from app.services.case_query_service import CaseQueryService
from app.services.case_retrieval_service import CaseRetrievalService
from app.services.citation_verifier_service import CitationVerifierService
from app.services.evaluation_service import EvaluationService
from app.services.health_service import HealthService
from app.services.record_check_service import RecordCheckService
from app.services.record_checks.laterality_check import LateralityCheck
from app.services.record_checks.patient_age_check import PatientAgeCheck
from app.services.record_checks.timely_filing_exception_check import (
    TimelyFilingExceptionCheck,
)
from app.services.rules.authorization_rule import AuthorizationRule
from app.services.rules.clinical_review_rule import ClinicalReviewRule
from app.services.rules.correction_route_rule import CorrectionRouteRule
from app.services.rules.denial_response_rule import DenialResponseRule
from app.services.rules.duplicate_rule import DuplicateRule
from app.services.rules.filing_limit_rule import FilingLimitRule
from app.services.rules.late_entry_rule import LateEntryRule
from app.services.rules.note_date_rule import NoteDateRule
from app.services.rules.procedure_conditions_rule import ProcedureConditionsRule
from app.services.rules.repeat_line_rule import RepeatLineRule
from app.services.rules.response_window_rule import ResponseWindowRule
from app.services.rules.side_modifier_rule import SideModifierRule
from app.services.rules.visit_modifier_rule import VisitModifierRule
from app.services.rules_engine_service import RulesEngineService
from app.services.sample_service import SampleService
from app.services.structured_llm_service import StructuredLlmService
from app.services.triage_guards.escalation_finding_guard import EscalationFindingGuard
from app.services.triage_guards.payer_error_guard import PayerErrorGuard
from app.services.triage_guards.visit_documentation_guard import VisitDocumentationGuard
from app.services.two_stage_verifier_service import TwoStageVerifierService


class ServiceContainer(containers.DeclarativeContainer):
    settings = providers.Dependency(instance_of=Settings)
    repositories = providers.DependenciesContainer()
    utilities = providers.DependenciesContainer()
    clients = providers.DependenciesContainer()

    health_service = providers.Factory(
        HealthService,
        health_repository=repositories.health_repository,
        clock=utilities.clock,
        agent_llm=clients.agent_llm,
        judge_llm=clients.judge_llm,
    )

    # A new rule is a new class added to this list; nothing else changes.
    rules = providers.List(
        providers.Factory(FilingLimitRule),
        providers.Factory(ResponseWindowRule),
        providers.Factory(DuplicateRule),
        providers.Factory(RepeatLineRule),
        providers.Factory(AuthorizationRule),
        providers.Factory(SideModifierRule),
        providers.Factory(VisitModifierRule),
        providers.Factory(NoteDateRule),
        providers.Factory(LateEntryRule),
        providers.Factory(ProcedureConditionsRule),
        providers.Factory(ClinicalReviewRule),
        # Last, so the clauses that state a requirement come before those on what follows.
        providers.Factory(DenialResponseRule),
    )
    # Checks on the facts extracted from the record, run after the record review.
    record_checks = providers.List(
        providers.Factory(LateralityCheck),
        providers.Factory(PatientAgeCheck),
        providers.Factory(TimelyFilingExceptionCheck),
    )
    record_check_service = providers.Factory(
        RecordCheckService,
        checks=record_checks,
        quote_matcher=utilities.quote_matcher,
        policy_repository=repositories.policy_repository,
    )
    # Rules that read the findings of the rules above.
    finding_rules = providers.List(
        providers.Factory(CorrectionRouteRule),
    )
    case_projection_service = providers.Factory(
        CaseProjectionService,
        case_repository=repositories.case_repository,
        clock=utilities.clock,
    )
    case_query_service = providers.Factory(
        CaseQueryService,
        include_visit_note=settings.provided.retrieval_include_visit_note,
    )
    # One instance per process: it keeps each payer's clauses tokenised.
    policy_retrieval_service = providers.Singleton(
        Bm25PolicyRetrievalService,
        policy_repository=repositories.policy_repository,
        tokenizer=utilities.tokenizer,
        scorer=utilities.text_scorer,
    )
    case_retrieval_service = providers.Factory(
        CaseRetrievalService,
        policy_repository=repositories.policy_repository,
        case_query_service=case_query_service,
        policy_retrieval_service=policy_retrieval_service,
        limit=settings.provided.retrieval_limit,
        neighbour_sources=settings.provided.retrieval_neighbour_sources,
        document_additions=settings.provided.retrieval_document_additions,
    )
    evaluation_service = providers.Factory(
        EvaluationService, evaluation_repository=repositories.evaluation_repository
    )
    sample_service = providers.Factory(
        SampleService,
        sample_repository=repositories.sample_repository,
        date_shifter=utilities.date_shifter,
        clock=utilities.clock,
    )

    # The agents share one model caller, bound to the agent model.
    agent_structured_llm = providers.Factory(
        StructuredLlmService, llm=clients.agent_llm, max_attempts=MAX_OUTPUT_ATTEMPTS
    )
    intake_agent_service = providers.Factory(
        IntakeAgentService, structured_llm=agent_structured_llm, renderer=utilities.case_renderer
    )
    # Checks by code on the action triage chose, highest priority first.
    triage_guards = providers.List(
        providers.Factory(EscalationFindingGuard),
        providers.Factory(VisitDocumentationGuard),
        providers.Factory(PayerErrorGuard),
    )
    triage_agent_service = providers.Factory(
        TriageAgentService,
        structured_llm=agent_structured_llm,
        renderer=utilities.case_renderer,
        guards=triage_guards,
    )
    writer_agent_service = providers.Factory(
        WriterAgentService,
        structured_llm=agent_structured_llm,
        renderer=utilities.case_renderer,
        quote_matcher=utilities.quote_matcher,
    )
    # The judge has its own model caller, bound to the judge model: a different
    # provider from the agents', so the writer's model does not grade its own work.
    judge_structured_llm = providers.Factory(
        StructuredLlmService, llm=clients.judge_llm, max_attempts=MAX_OUTPUT_ATTEMPTS
    )
    judge_agent_service = providers.Factory(
        JudgeAgentService, structured_llm=judge_structured_llm, renderer=utilities.case_renderer
    )
    citation_check_service = providers.Factory(
        CitationVerifierService, quote_matcher=utilities.quote_matcher
    )
    verifier_service = providers.Factory(
        TwoStageVerifierService,
        citation_check_service=citation_check_service,
        judge_agent_service=judge_agent_service,
    )

    rules_engine_service = providers.Factory(
        RulesEngineService,
        policy_repository=repositories.policy_repository,
        rules=rules,
        finding_rules=finding_rules,
    )
