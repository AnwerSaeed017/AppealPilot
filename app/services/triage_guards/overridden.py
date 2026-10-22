from app.schemas.recommended_action import RecommendedAction
from app.schemas.triage_decision import TriageDecision


def overridden(
    decision: TriageDecision, action: RecommendedAction, reasons: tuple[str, ...]
) -> TriageDecision:
    """The decision with its action replaced, the code's reasons first, the model's after."""
    return TriageDecision(
        action=action,
        confidence=decision.confidence,
        reasons=(*reasons, f"The model had chosen {decision.action.value}:", *decision.reasons),
    )
