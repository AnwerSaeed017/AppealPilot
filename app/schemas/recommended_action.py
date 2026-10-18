from enum import StrEnum


class RecommendedAction(StrEnum):
    """The five outcomes triage can choose between."""

    CORRECT_AND_RESUBMIT = "CORRECT_AND_RESUBMIT"
    APPEAL_WITH_EVIDENCE = "APPEAL_WITH_EVIDENCE"
    REQUEST_DOCUMENTATION = "REQUEST_DOCUMENTATION"
    NO_ACTION = "NO_ACTION"
    ESCALATE_TO_HUMAN = "ESCALATE_TO_HUMAN"
