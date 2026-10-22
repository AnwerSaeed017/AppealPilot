from app.schemas.base_schema import BaseSchema
from app.schemas.case_input import CaseInput
from app.schemas.finding import Finding, FindingCode
from app.schemas.note_fact import NoteFact
from app.schemas.payer_rule_set import PayerRuleSet


class RecordCheckContext(BaseSchema):
    """Everything one record check may look at, once the record has been read."""

    case_input: CaseInput
    payer_rules: PayerRuleSet
    # Only facts whose quotes were found in their documents.
    facts: tuple[NoteFact, ...]
    # What the rules established before the record was read.
    findings: tuple[Finding, ...]

    def has_finding(self, code: FindingCode) -> bool:
        return any(finding.code == code for finding in self.findings)
