"""The workflow engine's tables, all in the `workflow` schema.

These four tables are read and written by the workflow engine, never by the
application. Their columns are the ones the engine expects and must not be changed on
their own; see docs/agents.md, "State persistence".
"""

from typing import Any

from sqlalchemy import Integer, LargeBinary, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.constants.database import WORKFLOW_SCHEMA
from app.models.base import Base


class Checkpoint(Base):
    """One saved snapshot of a case's workflow state."""

    __tablename__ = "checkpoints"
    __table_args__ = {"schema": WORKFLOW_SCHEMA}

    thread_id: Mapped[str] = mapped_column(Text, primary_key=True, index=True)
    checkpoint_ns: Mapped[str] = mapped_column(Text, primary_key=True, server_default="")
    checkpoint_id: Mapped[str] = mapped_column(Text, primary_key=True)
    parent_checkpoint_id: Mapped[str | None] = mapped_column(Text)
    type: Mapped[str | None] = mapped_column(Text)
    checkpoint: Mapped[dict[str, Any]] = mapped_column(JSONB)
    # "metadata" is reserved on SQLAlchemy models, so the attribute has another name.
    checkpoint_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, server_default=text("'{}'")
    )


class CheckpointBlob(Base):
    """A value of one state field at one version, stored apart from the snapshot."""

    __tablename__ = "checkpoint_blobs"
    __table_args__ = {"schema": WORKFLOW_SCHEMA}

    thread_id: Mapped[str] = mapped_column(Text, primary_key=True, index=True)
    checkpoint_ns: Mapped[str] = mapped_column(Text, primary_key=True, server_default="")
    channel: Mapped[str] = mapped_column(Text, primary_key=True)
    version: Mapped[str] = mapped_column(Text, primary_key=True)
    type: Mapped[str] = mapped_column(Text)
    blob: Mapped[bytes | None] = mapped_column(LargeBinary)


class CheckpointWrite(Base):
    """What a step wrote before its snapshot was complete, so a step that was
    interrupted can be picked up where it stopped."""

    __tablename__ = "checkpoint_writes"
    __table_args__ = {"schema": WORKFLOW_SCHEMA}

    thread_id: Mapped[str] = mapped_column(Text, primary_key=True, index=True)
    checkpoint_ns: Mapped[str] = mapped_column(Text, primary_key=True, server_default="")
    checkpoint_id: Mapped[str] = mapped_column(Text, primary_key=True)
    task_id: Mapped[str] = mapped_column(Text, primary_key=True)
    idx: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel: Mapped[str] = mapped_column(Text)
    type: Mapped[str | None] = mapped_column(Text)
    blob: Mapped[bytes] = mapped_column(LargeBinary)
    task_path: Mapped[str] = mapped_column(Text, server_default="")


class CheckpointMigration(Base):
    """Which version of its own table layout the workflow engine finds here.

    One row per version, from 0 up. The Alembic migration that creates these tables
    also fills this in, so the engine knows the layout is already current.
    """

    __tablename__ = "checkpoint_migrations"
    __table_args__ = {"schema": WORKFLOW_SCHEMA}

    v: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
