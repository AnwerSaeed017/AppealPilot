import pytest

from app.clients.llm.errors import LlmRequestError
from app.clients.llm.mock_llm_client import MockLlmClient
from app.schemas.llm import LlmMessage, LlmRequest


def request_for(task: str) -> LlmRequest:
    return LlmRequest(
        task=task,
        prompt_version="1",
        messages=(LlmMessage(role="user", content="hello"),),
    )


async def test_returns_the_scripted_text_for_the_task() -> None:
    client = MockLlmClient(responses={"triage": '{"action": "NO_ACTION"}'})

    response = await client.complete(request_for("triage"))

    assert response.text == '{"action": "NO_ACTION"}'
    assert (response.provider, response.model) == ("mock", "mock")
    assert response.cached is False


async def test_unscripted_task_is_an_error_not_an_invented_answer() -> None:
    client = MockLlmClient()

    with pytest.raises(LlmRequestError, match="no response for task 'writer'"):
        await client.complete(request_for("writer"))


async def test_records_calls_in_order() -> None:
    client = MockLlmClient(responses={"a": "1", "b": "2"})

    await client.complete(request_for("a"))
    await client.complete(request_for("b"))

    assert [call.task for call in client.calls] == ["a", "b"]
