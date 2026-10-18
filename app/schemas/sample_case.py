from datetime import date

from pydantic import Field

from app.schemas.base_schema import BaseSchema
from app.schemas.case_input import CaseInput


class SampleCase(BaseSchema):
    """A synthetic case offered for a one-click run.

    `as_of_date` is the day the case was written for: its deadlines are set against it.
    """

    sample_id: str = Field(pattern=r"^[a-z0-9-]+$")
    title: str = Field(min_length=1, max_length=120)
    summary: str = Field(min_length=1, max_length=500)
    as_of_date: date
    input: CaseInput
