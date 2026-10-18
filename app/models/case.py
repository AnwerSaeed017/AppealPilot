"""The application's own record of cases and of each step of their runs.

These are for listing, following and reporting. The working state of a case is kept
separately by the workflow engine; see app/models/checkpoint.py.
"""

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CaseRecord(Base):
    """One denied claim being worked on."""

    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    claim_id: Mapped[str] = mapped_column(String(40))
    payer_id: Mapped[str] = mapped_column(String(12), index=True)
    carc_code: Mapped[str] = mapped_column(String(4))
    as_of: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), index=True)
    action: Mapped[str | None] = mapped_column(String(30))
    verified: Mapped[bool | None] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CaseAuditEventRecord(Base):
    """One step of a case's run. Rows are only ever added."""

    __tablename__ = "case_audit_events"

    case_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cases.id", ondelete="CASCADE"), primary_key=True
    )
    # Position in the run, from 1. With the case ID it is the key, so a step can be
    # recorded only once however many times the write is attempted.
    sequence: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    step: Mapped[str] = mapped_column(String(40))
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    summary: Mapped[str] = mapped_column(Text)
    # The remaining columns are set only for steps that called a model.
    provider: Mapped[str | None] = mapped_column(String(40))
    model: Mapped[str | None] = mapped_column(String(100))
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[float | None] = mapped_column(Float)
    cached: Mapped[bool | None] = mapped_column(Boolean)
    attempts: Mapped[int | None] = mapped_column(Integer)
