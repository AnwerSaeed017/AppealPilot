"""Groups of procedure codes that the rules treat alike."""

import re

# Office and outpatient visits, new and established patients (99202-99205, 99211-99215).
OFFICE_VISIT_CODE = re.compile(r"^992(0[2-5]|1[1-5])$")
