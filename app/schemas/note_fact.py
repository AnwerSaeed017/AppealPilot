from pydantic import Field

from app.schemas.base_schema import BaseSchema


class NoteFact(BaseSchema):
    """One fact taken from the visit note or a supporting document.

    The quote is the exact text it rests on, so that code can check it is really there.
    """

    statement: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    line_number: int = Field(ge=1)
    quote: str = Field(min_length=1)
    # True when the source words it as uncertain: "possible", "suspected", "may".
    hedged: bool = False


class NoteFacts(BaseSchema):
    """What the intake agent returns."""

    facts: tuple[NoteFact, ...] = ()
