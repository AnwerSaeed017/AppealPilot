from pydantic import Field

from app.schemas.base_schema import BaseSchema
from app.schemas.code_types import PayerId
from app.schemas.payer_rule_set import PayerRuleSet


class Payer(BaseSchema):
    """A payer and the rules code can apply for it.

    TESS and QUIL are invented and refer to no real organisation. MEDICARE is Original
    Medicare Part B, with rules and clauses quoted from published CMS sources.
    """

    payer_id: PayerId
    name: str = Field(min_length=1, max_length=100)
    rules: PayerRuleSet
