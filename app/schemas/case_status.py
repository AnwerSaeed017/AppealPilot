from enum import StrEnum


class CaseStatus(StrEnum):
    RUNNING = "RUNNING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    # The run stopped on an error before reaching the approval gate. It can be retried.
    FAILED = "FAILED"
