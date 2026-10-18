from app.schemas.api_response import ErrorDetail
from app.utilities.response_builder import ResponseBuilder
from tests.fakes import FIXED_NOW, FixedClock


def test_success_wraps_the_data() -> None:
    envelope = ResponseBuilder(FixedClock()).success({"id": 1})

    assert envelope.success is True
    assert envelope.data == {"id": 1}
    assert envelope.error is None
    assert envelope.meta.timestamp == FIXED_NOW


def test_failure_carries_code_message_and_details() -> None:
    envelope = ResponseBuilder(FixedClock()).failure(
        "validation_failed", "Not valid.", [ErrorDetail(field="claim_id", message="required")]
    )

    assert envelope.success is False
    assert envelope.data is None
    assert envelope.error is not None
    assert envelope.error.code == "validation_failed"
    assert envelope.error.details[0].field == "claim_id"
