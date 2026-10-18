from collections.abc import AsyncIterator

import httpx
import pytest
from fastapi import FastAPI

from app.core.exception_handlers import register_exception_handlers
from app.core.exceptions import ConflictError, DomainError, NotFoundError
from app.utilities.response_builder import ResponseBuilder
from tests.fakes import FixedClock


def build_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app, ResponseBuilder(FixedClock()))

    @app.get("/conflict")
    async def conflict() -> None:
        raise ConflictError("Already decided.")

    @app.get("/missing")
    async def missing() -> None:
        raise NotFoundError("No such case.")

    @app.get("/unmapped")
    async def unmapped() -> None:
        raise DomainError("Something about the request is wrong.")

    @app.get("/crash")
    async def crash() -> None:
        raise RuntimeError("internal detail that must not leak")

    @app.get("/typed/{number}")
    async def typed(number: int) -> int:
        return number

    return app


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=build_app(), raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


@pytest.mark.parametrize(
    ("path", "status", "code"),
    [
        ("/conflict", 409, "conflict"),
        ("/missing", 404, "not_found"),
        ("/unmapped", 400, "domain_error"),
    ],
)
async def test_domain_error_maps_to_its_status(
    client: httpx.AsyncClient, path: str, status: int, code: str
) -> None:
    response = await client.get(path)

    assert response.status_code == status
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == code


async def test_domain_error_message_reaches_the_client(client: httpx.AsyncClient) -> None:
    response = await client.get("/conflict")

    assert response.json()["error"]["message"] == "Already decided."


async def test_unexpected_error_returns_a_generic_500(client: httpx.AsyncClient) -> None:
    response = await client.get("/crash")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "internal detail" not in response.text


async def test_request_validation_error_names_the_field(client: httpx.AsyncClient) -> None:
    response = await client.get("/typed/not-a-number")

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_failed"
    assert error["details"][0]["field"] == "path.number"
    assert "not-a-number" not in response.text


async def test_method_not_allowed_uses_the_envelope(client: httpx.AsyncClient) -> None:
    response = await client.post("/conflict")

    assert response.status_code == 405
    assert response.json()["error"]["code"] == "method_not_allowed"
