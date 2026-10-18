import asyncio
import logging
import sys
from logging.config import fileConfig
from pathlib import Path
from typing import Any

from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context
from app.constants.database import WORKFLOW_SCHEMA
from app.core.settings import Settings
from app.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
logger = logging.getLogger("alembic.env")

# Importing app.models registers every table on this metadata.
target_metadata = Base.metadata
database_url = Settings().sqlalchemy_database_url

# The schemas this application owns. Tables anywhere else are left alone.
_OWN_SCHEMAS = {None, WORKFLOW_SCHEMA}

# Database functions, one per file. Loaded after the tables they use exist.
SQL_DIR = Path(__file__).resolve().parents[1] / "app" / "sql"
_HEAD_TARGETS = {"head", "heads"}


def _include_name(name: str | None, type_: str, parent_names: Any) -> bool:
    return name in _OWN_SCHEMAS if type_ == "schema" else True


def _upgrading_to_head() -> bool:
    """True for `alembic upgrade head`, and for nothing else: not check, current,
    revision or downgrade, which must not change the database's functions."""
    try:
        target = context.get_revision_argument()
    except KeyError:
        # Commands such as check and current have no target revision.
        return False
    if isinstance(target, tuple):
        target = target[0] if len(target) == 1 else None
    return target in _HEAD_TARGETS or (target is not None and target == context.get_head_revision())


def _load_sql_files() -> None:
    """Create or replace every database function in app/sql, in path order.

    Each file drops and recreates its own function, so loading them again is always
    safe and a changed signature is picked up.
    """
    paths = sorted(SQL_DIR.rglob("*.sql"))
    for path in paths:
        context.execute(path.read_text(encoding="utf-8"))
    logger.info("Loaded %d SQL files from %s", len(paths), SQL_DIR)


def _configure(**options: Any) -> None:
    context.configure(
        target_metadata=target_metadata,
        include_schemas=True,
        include_name=_include_name,
        compare_type=True,
        **options,
    )


def _migrate() -> None:
    with context.begin_transaction():
        context.run_migrations()
        # In the same transaction, so a failing SQL file rolls the whole upgrade back.
        if _upgrading_to_head():
            _load_sql_files()


def run_migrations_offline() -> None:
    _configure(url=database_url, literal_binds=True, dialect_opts={"paramstyle": "named"})
    _migrate()


def _run_migrations(connection: Connection) -> None:
    _configure(connection=connection)
    _migrate()


async def run_migrations_online() -> None:
    engine = create_async_engine(database_url)
    async with engine.connect() as connection:
        await connection.run_sync(_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    # The PostgreSQL driver cannot run on Windows' default event loop.
    asyncio.run(
        run_migrations_online(),
        loop_factory=asyncio.SelectorEventLoop if sys.platform == "win32" else None,
    )
