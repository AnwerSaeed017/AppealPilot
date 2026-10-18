from dependency_injector import containers, providers

from app.core.settings import Settings
from app.database.database import Database
from app.interfaces.database.sql_function_caller import ISqlFunctionCaller
from app.repositories.case_repository import CaseRepository
from app.repositories.file_policy_repository import FilePolicyRepository
from app.repositories.file_sample_repository import FileSampleRepository
from app.repositories.health_repository import HealthRepository


class RepositoryContainer(containers.DeclarativeContainer):
    settings = providers.Dependency(instance_of=Settings)
    database = providers.Dependency(instance_of=Database)
    sql_function_caller: providers.Dependency[ISqlFunctionCaller] = providers.Dependency()

    health_repository = providers.Factory(
        HealthRepository, session_factory=database.provided.session
    )
    case_repository = providers.Factory(
        CaseRepository, session_factory=database.provided.session, sql=sql_function_caller
    )
    # One instance per process: it holds the sample files after reading them once.
    sample_repository = providers.Singleton(
        FileSampleRepository, samples_dir=settings.provided.samples_dir
    )
    # One instance per process: it holds the policy files after reading them once.
    policy_repository = providers.Singleton(
        FilePolicyRepository, policies_dir=settings.provided.policies_dir
    )
