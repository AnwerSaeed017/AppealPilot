from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest

from app.core.exceptions import NotFoundError
from app.interfaces.repository.evaluation_repository import IEvaluationRepository
from app.main import app
from app.repositories.file_evaluation_repository import FileEvaluationRepository
from app.schemas.evaluation import EvaluationBenchmarks
from app.services.evaluation_service import EvaluationService

PUBLISHED = Path("seeders/evaluations/benchmarks.json")


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


async def test_the_published_results_are_served_in_the_envelope(
    client: httpx.AsyncClient,
) -> None:
    response = await client.get("/evaluations")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    benchmarks = EvaluationBenchmarks.model_validate(body["data"])
    run = benchmarks.run
    # Both systems ran the same labelled cases.
    assert run.correct.workflow.total == run.correct.baseline.total == run.labelled_cases


def test_the_published_file_holds_one_complete_run() -> None:
    benchmarks = EvaluationBenchmarks.model_validate_json(PUBLISHED.read_text(encoding="utf-8"))

    # Every case either system got wrong is listed, and none twice.
    ids = [outcome.case_id for outcome in benchmarks.run.misses]
    assert len(ids) == len(set(ids))
    assert benchmarks.run.paired.cases <= benchmarks.run.labelled_cases


async def test_a_missing_results_file_reads_as_nothing_published(tmp_path: Path) -> None:
    repository = FileEvaluationRepository(tmp_path / "absent.json")

    assert await repository.get() is None


class NothingPublished(IEvaluationRepository):
    async def get(self) -> EvaluationBenchmarks | None:
        return None


async def test_the_service_reports_not_found_when_nothing_is_published() -> None:
    with pytest.raises(NotFoundError, match="No evaluation results"):
        await EvaluationService(NothingPublished()).get()
