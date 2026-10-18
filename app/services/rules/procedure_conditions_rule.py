from app.constants.denial_codes import PROCEDURE_CONDITION_DENIALS
from app.interfaces.service.rule import IRule
from app.schemas.finding import Finding, FindingCode
from app.schemas.rule_context import RuleContext


class ProcedureConditionsRule(IRule):
    """Names the clause that sets the conditions for each denied procedure.

    It applies to denials about diagnosis support, medical necessity and missing
    documentation. It says which clause governs the procedure and nothing about
    whether the conditions were met, which is a judgement about the record.
    """

    def check(self, context: RuleContext) -> tuple[Finding, ...]:
        if context.case_input.denial.carc_code not in PROCEDURE_CONDITION_DENIALS:
            return ()
        procedure_clauses = context.payer_rules.procedure_clauses
        return tuple(
            Finding(
                code=FindingCode.PROCEDURE_CONDITIONS_CLAUSE,
                message=(
                    f"The conditions for procedure code {line.procedure_code} on line "
                    f"{line.line_number} are set by clause "
                    f"{procedure_clauses[line.procedure_code]}."
                ),
                clause_ids=(procedure_clauses[line.procedure_code],),
                line_numbers=(line.line_number,),
            )
            for line in context.denied_lines()
            if line.procedure_code in procedure_clauses
        )
