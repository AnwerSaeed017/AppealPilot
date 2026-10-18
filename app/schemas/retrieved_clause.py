from pydantic import Field

from app.schemas.base_schema import BaseSchema
from app.schemas.policy_clause import PolicyClause


class RetrievedClause(BaseSchema):
    """A clause returned by a search, with its position in the results."""

    clause: PolicyClause
    rank: int = Field(ge=1)
    score: float = Field(gt=0)
