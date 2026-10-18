import pytest
from pydantic import BaseModel

from app.clients.llm.errors import LlmResponseError
from app.core.exceptions import AgentOutputError
from app.interfaces.clients.llm_client import ILlmClient
from app.schemas.llm import LlmRequest, LlmResponse, LlmUsage
from app.services.structured_llm_service import StructuredLlmService


class Answer(BaseModel):
    action: str
    confidence: float


class ScriptedLlmClient(ILlmClient):
    """Returns the given replies in order and records what it was asked."""

    def __init__(self, replies: list[str]) -> None:
        self._replies = list(replies)
        self.requests: list[LlmRequest] = []

    @property
    def provider(self) -> str:
        return "scripted"

    @property
    def model(self) -> str:
        return "scripted-1"

    async def complete(self, request: LlmRequest) -> LlmResponse:
        self.requests.append(request)
        return LlmResponse(
            text=self._replies.pop(0),
            provider=self.provider,
            model=self.model,
            usage=LlmUsage(input_tokens=100, output_tokens=20),
            latency_ms=50.0,
        )


VALID = '{"action": "NO_ACTION", "confidence": 0.9}'


async def ask(client: ScriptedLlmClient, max_attempts: int = 3) -> Answer:
    result = await StructuredLlmService(client, max_attempts).complete(
        task="triage",
        prompt_version="1",
        system="You decide.",
        user="Decide.",
        output_type=Answer,
        max_output_tokens=200,
    )
    return result.output


async def test_valid_reply_is_returned_after_one_call() -> None:
    client = ScriptedLlmClient([VALID])

    result = await StructuredLlmService(client, 3).complete(
        "triage", "1", "You decide.", "Decide.", Answer, 200
    )

    assert result.output == Answer(action="NO_ACTION", confidence=0.9)
    assert result.llm_call.attempts == 1
    assert (result.llm_call.input_tokens, result.llm_call.output_tokens) == (100, 20)
    assert len(client.requests) == 1


async def test_request_asks_for_json_and_includes_the_schema() -> None:
    client = ScriptedLlmClient([VALID])

    await ask(client)

    request = client.requests[0]
    assert request.json_output is True
    assert request.task == "triage"
    assert '"confidence"' in request.messages[1].content
    assert request.messages[0].role == "system"


async def test_reply_in_a_code_fence_is_accepted() -> None:
    assert (await ask(ScriptedLlmClient([f"```json\n{VALID}\n```"]))).action == "NO_ACTION"


@pytest.mark.parametrize(
    "bad_reply",
    [
        "I think the answer is NO_ACTION.",  # not JSON
        '{"action": "NO_ACTION"}',  # a required field is missing
        '{"action": "NO_ACTION", "confidence": "high"}',  # wrong type
    ],
)
async def test_invalid_reply_is_sent_back_with_the_reason(bad_reply: str) -> None:
    client = ScriptedLlmClient([bad_reply, VALID])

    result = await StructuredLlmService(client, 3).complete(
        "triage", "1", "You decide.", "Decide.", Answer, 200
    )

    assert result.output.action == "NO_ACTION"
    assert result.llm_call.attempts == 2
    # Tokens and time of the failed attempt are counted too.
    assert result.llm_call.input_tokens == 200
    assert result.llm_call.latency_ms == 100.0

    second = client.requests[1].messages
    assert [message.role for message in second] == ["system", "user", "assistant", "user"]
    assert second[2].content == bad_reply
    assert "not valid" in second[3].content


async def test_validation_errors_tell_the_model_which_field_is_wrong() -> None:
    client = ScriptedLlmClient(['{"action": "NO_ACTION"}', VALID])

    await ask(client)

    assert "confidence" in client.requests[1].messages[3].content


async def test_gives_up_after_the_allowed_attempts() -> None:
    client = ScriptedLlmClient(["nope", "still nope", "no"])

    with pytest.raises(AgentOutputError, match="triage step did not return usable output in 3"):
        await ask(client)

    assert len(client.requests) == 3


async def test_attempt_limit_is_respected() -> None:
    client = ScriptedLlmClient(["nope", VALID])

    with pytest.raises(AgentOutputError):
        await ask(client, max_attempts=1)

    assert len(client.requests) == 1


class UnreadableThenValidClient(ScriptedLlmClient):
    """The provider rejects its own first reply as invalid JSON, then answers properly."""

    def __init__(self) -> None:
        super().__init__([VALID])
        self.failed_once = False

    async def complete(self, request: LlmRequest) -> LlmResponse:
        if not self.failed_once:
            self.failed_once = True
            self.requests.append(request)
            raise LlmResponseError("groq could not produce valid JSON")
        return await super().complete(request)


async def test_a_reply_the_provider_could_not_read_is_asked_again() -> None:
    client = UnreadableThenValidClient()

    result = await StructuredLlmService(client, 3).complete(
        "triage", "1", "You decide.", "Decide.", Answer, 200
    )

    assert result.output.action == "NO_ACTION"
    assert result.llm_call.attempts == 2
    second = client.requests[1].messages
    assert [message.role for message in second] == ["system", "user"]
    assert "could not be read as JSON" in second[1].content
