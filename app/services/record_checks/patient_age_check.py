from datetime import date

from app.constants.record_checks import AGE_TOLERANCE_YEARS, STATED_AGE
from app.interfaces.service.record_check import IRecordCheck
from app.schemas.finding import Finding, FindingCode
from app.schemas.record_check_context import RecordCheckContext


def _age_on(birth: date, day: date) -> int:
    return day.year - birth.year - ((day.month, day.day) < (birth.month, birth.day))


class PatientAgeCheck(IRecordCheck):
    """Finds a document that states an age the claim's patient could not have had.

    The claim's date of birth gives the patient's age on the day of the visit; a document
    that says otherwise is most likely about someone else.
    """

    def check(self, context: RecordCheckContext) -> tuple[Finding, ...]:
        case_input = context.case_input
        age = _age_on(case_input.claim.patient_date_of_birth, case_input.visit_note.encounter_date)
        for fact in context.facts:
            for stated in STATED_AGE.findall(fact.quote):
                if abs(int(stated) - age) > AGE_TOLERANCE_YEARS:
                    return (
                        Finding(
                            code=FindingCode.DOCUMENT_PATIENT_MISMATCH,
                            message=(
                                f"{fact.document_id} line {fact.line_number} describes a "
                                f'{stated}-year-old ("{fact.quote}"), but the date of birth '
                                f"on the claim makes the patient {age} at the visit."
                            ),
                        ),
                    )
        return ()
