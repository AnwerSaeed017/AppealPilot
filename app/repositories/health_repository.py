import logging

from sqlalchemy import literal, select
from sqlalchemy.exc import SQLAlchemyError

from app.database.session_factory import SessionFactory
from app.interfaces.repository.health_repository import IHealthRepository

logger = logging.getLogger(__name__)


class HealthRepository(IHealthRepository):
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    async def is_database_reachable(self) -> bool:
        try:
            async with self._session_factory() as session:
                # A trivial query built by SQLAlchemy, so it runs on any database.
                await session.execute(select(literal(1)))
        except (SQLAlchemyError, OSError):
            logger.exception("Database connectivity check failed")
            return False
        return True
