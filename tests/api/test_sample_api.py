import json
from collections.abc import AsyncIterator
from datetime import date
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.main import app
from app.schemas.case_input import CaseInput
from app.utilities.iso_date_shifter import IsoDateShifter

SAMPLES_DIR = Path("seeders/samples")


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


def written(sample_id: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((SAMPLES_DIR / f"{sample_id}.json").read_text("utf-8"))
    return data


async def test_every_sample_is_listed_dated_today_and_valid(client: httpx.AsyncClient) -> None:
    response = await client.get("/samples")

    assert response.status_code == 200
    samples = response.json()["data"]
    assert len(samples) == len(list(SAMPLES_DIR.glob("*.json"))) == 3
    for sample in samples:
        assert sample["as_of_date"] == date.today().isoformat()
        CaseInput.model_validate(sample["input"])  # still a valid submission


async def test_deadlines_are_as_near_as_on_the_day_the_sample_was_written(
    client: httpx.AsyncClient,
) -> None:
    sample = next(
        item
        for item in (await client.get("/samples")).json()["data"]
        if item["sample_id"] == "claim-filed-after-one-year"
    )
    original = written("claim-filed-after-one-year")

    def days_before_as_of(payload: dict[str, Any], as_of: str, field: str) -> int:
        return (date.fromisoformat(as_of) - date.fromisoformat(payload["denial"][field])).days

    def days_to_submit(payload: dict[str, Any]) -> int:
        claim = payload["claim"]
        service = date.fromisoformat(claim["lines"][0]["service_date"])
        return (date.fromisoformat(claim["submitted_date"]) - service).days

    assert days_before_as_of(sample["input"], sample["as_of_date"], "denial_date") == (
        days_before_as_of(original["input"], original["as_of_date"], "denial_date")
    )
    # The claim is still filed late by the same margin.
    assert days_to_submit(sample["input"]) == days_to_submit(original["input"]) > 365


async def test_every_sample_is_a_medicare_claim(client: httpx.AsyncClient) -> None:
    samples = (await client.get("/samples")).json()["data"]

    assert {sample["input"]["claim"]["payer_id"] for sample in samples} == {"MEDICARE"}


async def test_dates_inside_the_note_move_with_the_claim(client: httpx.AsyncClient) -> None:
    sample = next(
        item
        for item in (await client.get("/samples")).json()["data"]
        if item["sample_id"] == "claim-filed-after-one-year"
    )

    note = sample["input"]["visit_note"]
    assert f"Date of visit: {note['encounter_date']}" in note["text"]


def test_the_shifter_moves_dates_anywhere_and_leaves_the_rest() -> None:
    value = {
        "date": "2026-06-16",
        "text": "Seen 2026-06-16; review 2026-07-01. Code M17.11, ref 2026-99-99.",
        "items": ["2026-12-31", 3, None],
    }

    moved = IsoDateShifter().shift(value, 1)

    assert moved == {
        "date": "2026-06-17",
        "text": "Seen 2026-06-17; review 2026-07-02. Code M17.11, ref 2026-99-99.",
        "items": ["2027-01-01", 3, None],
    }
