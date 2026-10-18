from pydantic import Field

from app.schemas.audit_event import LlmCallRecord
from app.schemas.base_schema import BaseSchema


class AssertionVerdict(BaseSchema):
    """The result of checking one assertion's citations."""

    assertion_index: int = Field(ge=0)
    supported: bool
    problems: tuple[str, ...] = ()


class VerificationReport(BaseSchema):
    verdicts: tuple[AssertionVerdict, ...] = ()

    @property
    def passed(self) -> bool:
        """True only when every assertion is supported. An empty draft passes."""
        return all(verdict.supported for verdict in self.verdicts)

    def failures(self) -> tuple[AssertionVerdict, ...]:
        return tuple(verdict for verdict in self.verdicts if not verdict.supported)


class JudgeVerdict(BaseSchema):
    """The model judge's view of one assertion."""

    assertion_index: int = Field(ge=0)
    supported: bool
    reason: str = Field(min_length=1)


class JudgeVerdicts(BaseSchema):
    """What the model judge returns."""

    verdicts: tuple[JudgeVerdict, ...] = ()


class Verification(BaseSchema):
    """The outcome of verifying a draft, and what the model judge cost if it ran."""

    report: VerificationReport
    llm_call: LlmCallRecord | None = None
