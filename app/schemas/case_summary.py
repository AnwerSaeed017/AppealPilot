"""What the case tables hold: one row per case, and one row per step of its run."""

from datetime import date, datetime

from pydantic import Field

from app.agents.states.case_state import CaseState
from app.schemas.audit_event import AuditEvent
from app.schemas.base_schema import BaseSchema
from app.schemas.case_status import CaseStatus
from app.schemas.recommended_action import RecommendedAction


class CaseSnapshot(BaseSchema):
    """The facts about a case that the case table records, taken from its state."""

    case_id: str
    claim_id: str
    payer_id: str
    carc_code: str
    as_of: date
    status: CaseStatus
    action: RecommendedAction | None = None
    # None until the draft has been verified.
    verified: bool | None = None

    @classmethod
    def of(cls, state: CaseState) -> "CaseSnapshot":
        return cls(
            case_id=state.case_id,
            claim_id=state.case_input.claim.claim_id,
            payer_id=state.case_input.claim.payer_id,
            carc_code=state.case_input.denial.carc_code,
            as_of=state.as_of,
            status=state.status,
            action=state.triage.action if state.triage else None,
            verified=state.verification.passed if state.verification else None,
        )


class CaseSummary(CaseSnapshot):
    """A case as listed: its snapshot plus when it was opened and last changed."""

    created_at: datetime
    updated_at: datetime


class CaseEvent(BaseSchema):
    """One step of a case's run, with its position in the run."""

    sequence: int = Field(ge=1)
    event: AuditEvent


class CasePage(BaseSchema):
    items: tuple[CaseSummary, ...]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total: int = Field(ge=0)


class CaseView(BaseSchema):
    """A case as returned by the API.

    `state` is the full working state. It is absent for the first moments of a new
    case, before its first step has been saved.
    """

    summary: CaseSummary
    state: CaseState | None = None
