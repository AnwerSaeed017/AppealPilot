"""Fixed names used when talking to PostgreSQL."""

# URL scheme of a PostgreSQL address, and the same with the driver SQLAlchemy uses.
POSTGRES_SCHEME = "postgresql"
POSTGRES_SQLALCHEMY_DRIVER = "postgresql+psycopg"

# The schema holding the workflow engine's own tables. They are created and migrated by
# the engine, not by Alembic, and are kept apart from the application's tables.
WORKFLOW_SCHEMA = "workflow"
