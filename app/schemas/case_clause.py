from enum import StrEnum

from pydantic import Field

from app.schemas.base_schema import BaseSchema
from app.schemas.policy_clause import PolicyClause


class ClauseOrigin(StrEnum):
    """Why a clause is in front of the agents for a case."""

    RULE = "RULE"  # a rule finding cites it
    SEARCH = "SEARCH"  # the search matched it
    NEIGHBOUR = "NEIGHBOUR"  # it follows a top clause in the same section
    DOCUMENT = "DOCUMENT"  # a search on facts from the supporting documents matched it


class CaseClause(BaseSchema):
    """A clause selected for a case. Only these clauses may be cited for it."""

    clause: PolicyClause
    rank: int = Field(ge=1)
    origin: ClauseOrigin
