from collections.abc import Sequence
from datetime import date
from typing import Annotated

from app.schemas.audit_event import AuditEvent
from app.schemas.base_schema import BaseSchema
from app.schemas.case_clause import CaseClause
from app.schemas.case_input import CaseInput
from app.schemas.case_status import CaseStatus
from app.schemas.draft import Draft
from app.schemas.finding import Finding
from app.schemas.human_decision import HumanDecision
from app.schemas.note_fact import NoteFact
from app.schemas.triage_decision import TriageDecision
from app.schemas.verification_report import VerificationReport


def append_events(
    existing: Sequence[AuditEvent], added: Sequence[AuditEvent]
) -> tuple[AuditEvent, ...]:
    """Join new audit events to the trail.

    The trail comes back from storage as a list, so both sides are normalised first.
    """
    return (*existing, *added)


class CaseState(BaseSchema):
    """Everything known about one case as it moves through the workflow.

    Each node returns only the fields it changes. `audit` is the exception: what a node
    returns for it is appended, so the trail only ever grows.
    """

    case_id: str
    # The day the case is being worked on. Deadlines are judged against it.
    as_of: date
    case_input: CaseInput
    status: CaseStatus = CaseStatus.RUNNING

    findings: tuple[Finding, ...] = ()
    clauses: tuple[CaseClause, ...] = ()
    note_facts: tuple[NoteFact, ...] = ()
    triage: TriageDecision | None = None
    draft: Draft | None = None
    verification: VerificationReport | None = None
    # How many drafts the writer has produced, the first one included.
    writer_attempts: int = 0
    human_decision: HumanDecision | None = None

    audit: Annotated[tuple[AuditEvent, ...], append_events] = ()
