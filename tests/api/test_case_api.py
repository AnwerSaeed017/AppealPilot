"""The case endpoints, driving the real workflow on the mock model.

The checkpointer and the case repository are held in memory here, so these tests need
no database. A submitted case runs in the background; `settled` waits for it.
"""

import json
from collections.abc import AsyncIterator
from typing import Any, cast

import httpx
import pytest
from dependency_injector import providers
from langgraph.checkpoint.memory import InMemorySaver

from app.clients.llm.mock_llm_client import MockLlmClient
from app.main import app, container
from tests.fakes import InMemoryCaseRepository
from tests.unit.test_case_workflow import scripted_replies, side_modifier_case

CASE = side_modifier_case()
PAYLOAD: dict[str, Any] = CASE.input
STEPS_TO_THE_GATE = [
    "rules",
    "retrieval",
    "intake",
    "record_checks",
    "document_retrieval",
    "triage",
    "writer",
    "verifier",
    "review",
]


def fresh_workflow() -> None:
    """Drop the built workflow, so the next one picks up the overrides in force."""
    cast("providers.Singleton[Any]", container.agents.case_workflow).reset()


async def settled() -> None:
    """Wait for every case that is running in the background to stop."""
    await container.utilities.task_runner().drain()


@pytest.fixture
def mock() -> MockLlmClient:
    return MockLlmClient(scripted_replies(CASE))


@pytest.fixture
async def client(mock: MockLlmClient) -> AsyncIterator[httpx.AsyncClient]:
    fresh_workflow()
    with (
        container.clients.mock_llm.override(providers.Object(mock)),
        container.checkpointer.override(providers.Object(InMemorySaver())),
        container.repositories.case_repository.override(providers.Object(InMemoryCaseRepository())),
    ):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as http_client:
            yield http_client
        await settled()
    fresh_workflow()


async def submit(client: httpx.AsyncClient) -> str:
    """Submit the sample case, wait for it to reach the gate, and return its ID."""
    response = await client.post("/cases", json=PAYLOAD)
    assert response.status_code == 202, response.text
    case_id: str = response.json()["data"]["summary"]["case_id"]
    await settled()
    return case_id


async def view(client: httpx.AsyncClient, case_id: str) -> dict[str, Any]:
    response = await client.get(f"/cases/{case_id}")
    assert response.status_code == 200, response.text
    data: dict[str, Any] = response.json()["data"]
    return data


async def stream(client: httpx.AsyncClient, case_id: str) -> list[tuple[str, dict[str, Any]]]:
    """Every event of a case's stream, as (event name, data) pairs."""
    response = await client.get(f"/cases/{case_id}/events")
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/event-stream")
    events = []
    for block in response.text.strip().split("\n\n"):
        name, data = block.split("\n", 1)
        events.append((name.removeprefix("event: "), json.loads(data.removeprefix("data: "))))
    return events


def steps_of(events: list[tuple[str, dict[str, Any]]]) -> list[dict[str, Any]]:
    return [data["event"] for name, data in events if name == "step"]


async def test_submitting_answers_at_once_with_a_running_case(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post("/cases", json=PAYLOAD)

    assert response.status_code == 202
    summary = response.json()["data"]["summary"]
    assert summary["status"] == "RUNNING"
    assert summary["payer_id"] == "TESS"
    assert summary["action"] is None


async def test_a_submitted_case_runs_to_the_approval_gate(client: httpx.AsyncClient) -> None:
    case = await view(client, await submit(client))

    assert case["summary"]["status"] == "AWAITING_APPROVAL"
    assert case["summary"]["action"] == "CORRECT_AND_RESUBMIT"
    assert case["summary"]["verified"] is True
    assert case["state"]["triage"]["action"] == "CORRECT_AND_RESUBMIT"
    assert case["state"]["human_decision"] is None
    assert [event["step"] for event in case["state"]["audit"]] == STEPS_TO_THE_GATE


async def test_the_server_sets_the_case_id_and_the_working_date(
    client: httpx.AsyncClient,
) -> None:
    first, second = await submit(client), await submit(client)

    assert first != second
    assert len(first) == 36
    assert (await view(client, first))["summary"]["as_of"]


async def test_a_client_cannot_supply_server_fields(client: httpx.AsyncClient) -> None:
    response = await client.post("/cases", json=PAYLOAD | {"case_id": "MINE", "status": "APPROVED"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"


async def test_cases_are_listed_and_can_be_filtered_and_paged(
    client: httpx.AsyncClient,
) -> None:
    first, second = await submit(client), await submit(client)
    await client.post(f"/cases/{first}/decision", json={"kind": "APPROVE"})

    everything = (await client.get("/cases")).json()["data"]
    waiting = (await client.get("/cases", params={"status": "AWAITING_APPROVAL"})).json()["data"]
    second_page = (await client.get("/cases", params={"page": 2, "page_size": 1})).json()["data"]

    assert everything["total"] == 2
    assert {item["case_id"] for item in everything["items"]} == {first, second}
    assert [item["case_id"] for item in waiting["items"]] == [second]
    assert (second_page["total"], len(second_page["items"])) == (2, 1)


@pytest.mark.parametrize("params", [{"page": 0}, {"page_size": 0}, {"page_size": 101}])
async def test_list_paging_has_limits(client: httpx.AsyncClient, params: dict[str, int]) -> None:
    assert (await client.get("/cases", params=params)).status_code == 422


async def test_the_stream_gives_every_step_and_then_the_status(
    client: httpx.AsyncClient,
) -> None:
    events = await stream(client, await submit(client))

    assert [step["step"] for step in steps_of(events)] == STEPS_TO_THE_GATE
    assert [data["sequence"] for name, data in events if name == "step"] == list(range(1, 10))
    assert events[-1][0] == "status"
    assert events[-1][1]["status"] == "AWAITING_APPROVAL"


async def test_the_stream_records_what_each_model_step_cost(client: httpx.AsyncClient) -> None:
    by_step = {step["step"]: step for step in steps_of(await stream(client, await submit(client)))}

    assert by_step["writer"]["llm_call"]["provider"] == "mock"
    assert by_step["writer"]["llm_call"]["attempts"] == 1
    assert by_step["rules"]["llm_call"] is None


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/cases/no-such-case"),
        ("GET", "/cases/no-such-case/events"),
        ("POST", "/cases/no-such-case/retry"),
    ],
)
async def test_an_unknown_case_is_not_found(
    client: httpx.AsyncClient, method: str, path: str
) -> None:
    response = await client.request(method, path)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def test_deciding_an_unknown_case_is_not_found(client: httpx.AsyncClient) -> None:
    response = await client.post("/cases/no-such-case/decision", json={"kind": "APPROVE"})

    assert response.status_code == 404


async def test_approving_finishes_the_case(client: httpx.AsyncClient, mock: MockLlmClient) -> None:
    case_id = await submit(client)

    response = await client.post(f"/cases/{case_id}/decision", json={"kind": "APPROVE"})

    assert response.status_code == 200
    decided = response.json()["data"]
    assert decided["summary"]["status"] == "APPROVED"
    assert decided["state"]["human_decision"]["kind"] == "APPROVE"
    assert len(mock.calls) == 4  # deciding called no model
    recorded = [step["step"] for step in steps_of(await stream(client, case_id))]
    assert recorded == [*STEPS_TO_THE_GATE, "approval"]


async def test_rejecting_requires_a_reason(client: httpx.AsyncClient) -> None:
    url = f"/cases/{await submit(client)}/decision"

    without_reason = await client.post(url, json={"kind": "REJECT"})
    with_reason = await client.post(url, json={"kind": "REJECT", "reason": "Wrong knee."})

    assert without_reason.status_code == 422
    assert with_reason.status_code == 200
    assert with_reason.json()["data"]["summary"]["status"] == "REJECTED"


async def test_a_second_decision_is_a_conflict_and_changes_nothing(
    client: httpx.AsyncClient,
) -> None:
    case_id = await submit(client)
    url = f"/cases/{case_id}/decision"
    await client.post(url, json={"kind": "APPROVE"})

    again = await client.post(url, json={"kind": "REJECT", "reason": "Changed my mind."})

    assert again.status_code == 409
    assert again.json()["error"]["code"] == "conflict"
    assert (await view(client, case_id))["summary"]["status"] == "APPROVED"


@pytest.mark.parametrize(
    "broken",
    [
        {"claim": {**PAYLOAD["claim"], "billing_provider_npi": "1234567890"}},
        {"claim": {**PAYLOAD["claim"], "diagnosis_codes": ["M1711"]}},
        {"denial": {**PAYLOAD["denial"], "claim_id": "CLM-OTHER"}},
    ],
)
async def test_invalid_input_is_rejected_before_any_model_is_called(
    client: httpx.AsyncClient, mock: MockLlmClient, broken: dict[str, Any]
) -> None:
    response = await client.post("/cases", json=PAYLOAD | broken)
    await settled()

    assert response.status_code == 422
    assert mock.calls == ()
    assert (await client.get("/cases")).json()["data"]["total"] == 0


async def test_a_failed_run_is_marked_and_can_be_retried_from_where_it_stopped(
    client: httpx.AsyncClient,
) -> None:
    # First attempt: triage returns nothing usable, so the run stops there.
    broken = MockLlmClient(scripted_replies(CASE) | {"triage": "not json"})
    with container.clients.mock_llm.override(providers.Object(broken)):
        fresh_workflow()
        case_id = await submit(client)

    failed = await view(client, case_id)
    assert failed["summary"]["status"] == "FAILED"
    assert failed["state"]["status"] == "FAILED"
    assert failed["state"]["note_facts"]  # intake had finished and was saved
    assert (await stream(client, case_id))[-1][1]["status"] == "FAILED"

    # Second attempt, with a working model: the case continues, it does not start over.
    working = MockLlmClient(scripted_replies(CASE))
    with container.clients.mock_llm.override(providers.Object(working)):
        fresh_workflow()
        response = await client.post(f"/cases/{case_id}/retry")
        await settled()

    assert response.status_code == 202
    assert response.json()["data"]["summary"]["status"] == "RUNNING"
    assert (await view(client, case_id))["summary"]["status"] == "AWAITING_APPROVAL"
    assert [call.task for call in working.calls] == ["triage", "writer", "judge"]


async def test_only_a_failed_case_can_be_retried(client: httpx.AsyncClient) -> None:
    response = await client.post(f"/cases/{await submit(client)}/retry")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"
