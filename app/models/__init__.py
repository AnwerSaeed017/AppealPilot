"""Every table of the application.

Importing this package registers all models on `Base.metadata`, which is what Alembic
compares the database against. A new model module must be imported here.
"""

from app.models.base import Base
from app.models.case import CaseAuditEventRecord, CaseRecord
from app.models.checkpoint import (
    Checkpoint,
    CheckpointBlob,
    CheckpointMigration,
    CheckpointWrite,
)

__all__ = [
    "Base",
    "CaseAuditEventRecord",
    "CaseRecord",
    "Checkpoint",
    "CheckpointBlob",
    "CheckpointMigration",
    "CheckpointWrite",
]
