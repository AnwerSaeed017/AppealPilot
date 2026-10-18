from collections.abc import AsyncIterator

import httpx
import pytest
from dependency_injector import providers

from app.main import app, container
from tests.fakes import FakeHealthRepository


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


async def test_live_returns_the_envelope(client: httpx.AsyncClient) -> None:
    response = await client.get("/health/live")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"] == {"status": "alive"}
    assert body["error"] is None
    assert "timestamp" in body["meta"]


async def test_ready_checks_the_real_database(client: httpx.AsyncClient) -> None:
    response = await client.get("/health/ready")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["database"] == "ok"
    assert data["agent_llm"] == {"provider": "mock", "model": "mock"}


async def test_ready_returns_503_when_the_database_is_down(client: httpx.AsyncClient) -> None:
    with container.repositories.health_repository.override(
        providers.Object(FakeHealthRepository(reachable=False))
    ):
        response = await client.get("/health/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["success"] is False
    assert body["data"] is None
    assert body["error"]["code"] == "service_unavailable"


async def test_unknown_route_uses_the_envelope(client: httpx.AsyncClient) -> None:
    response = await client.get("/no-such-route")

    assert response.status_code == 404
    assert response.json()["error"] == {"code": "not_found", "message": "Not Found", "details": []}
