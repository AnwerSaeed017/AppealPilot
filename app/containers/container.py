from dependency_injector import containers, providers

from app.agents.container import AgentContainer
from app.clients.container import ClientContainer
from app.constants.database import WORKFLOW_SCHEMA
from app.core.settings import Settings
from app.database.checkpoint_types import checkpoint_types
from app.database.database import Database
from app.database.postgres_checkpoint_store import PostgresCheckpointStore
from app.database.sql_function_caller import SqlFunctionCaller
from app.repositories.container import RepositoryContainer
from app.services.case_service import CaseService
from app.services.container import ServiceContainer
from app.utilities.container import UtilityContainer


class Container(containers.DeclarativeContainer):
    """Root container: builds settings and the database, then wires the layers."""

    settings = providers.Singleton(Settings)

    database = providers.Singleton(
        Database,
        url=settings.provided.sqlalchemy_database_url,
        echo=settings.provided.database_echo,
    )

    # Calls the database functions in app/sql; repositories write no SQL of their own.
    sql_function_caller = providers.Singleton(SqlFunctionCaller)

    utilities = providers.Container(UtilityContainer)
    clients = providers.Container(ClientContainer, settings=settings)
    repositories = providers.Container(
        RepositoryContainer,
        settings=settings,
        database=database,
        sql_function_caller=sql_function_caller,
    )
    services = providers.Container(
        ServiceContainer,
        settings=settings,
        repositories=repositories,
        utilities=utilities,
        clients=clients,
    )

    # Where the state of every case is saved after each workflow step. main.py opens it
    # at start-up and closes it at shutdown. Keeping that state somewhere else means
    # changing this one provider.
    checkpoint_store = providers.Singleton(
        PostgresCheckpointStore,
        dsn=settings.provided.postgres_dsn,
        schema=WORKFLOW_SCHEMA,
        pool_max_size=settings.provided.checkpoint_pool_max_size,
        state_types=providers.Callable(checkpoint_types),
    )
    checkpointer = checkpoint_store.provided.saver
    agents = providers.Container(
        AgentContainer, services=services, utilities=utilities, checkpointer=checkpointer
    )

    # Defined here and not in the service container because it sits above the workflow,
    # which is itself built from the services.
    case_service = providers.Factory(
        CaseService,
        workflow=agents.case_workflow,
        projection=services.case_projection_service,
        case_repository=repositories.case_repository,
        clock=utilities.clock,
        id_generator=utilities.id_generator,
        task_runner=utilities.task_runner,
        poll_seconds=settings.provided.case_events_poll_seconds,
    )
