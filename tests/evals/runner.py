"""Run evaluation cases through the workflow and the single-prompt baseline.

    python -m tests.evals.runner                         run or resume the run "dev"
    python -m tests.evals.runner --limit 5 --pause 10    at most 5 cases, 10 s apart
    python -m tests.evals.runner --only graph            one system only
    python -m tests.evals.runner --fresh                 discard the run and start over
    python -m tests.evals.runner --retry-errors          also redo results that hit an error
    python -m tests.evals.runner --wait-for-quota 60     sleep through rate limits of up to 60 min
    python -m tests.evals.report                         write the report for a run

Each case's result is written as soon as the case finishes, to
tests/evals/results/<run>/<case_id>.json, so a run stopped for any reason resumes where
it left off. Model replies are cached on disk, so repeating a case costs nothing.

Each case is worked as of its own date, not today's, because its deadlines were written
against that date. Only the development cases are run; the locked cases need --release.

The workflow runs with an in-memory checkpointer and case record, so an evaluation run
writes nothing to the database.
"""

import argparse
import asyncio
import hashlib
import json
import logging
import shutil
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dependency_injector import providers
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import ValidationError

from app.agents.prompts import intake_prompt, judge_prompt, triage_prompt, writer_prompt
from app.agents.states.case_state import CaseState
from app.clients.llm.errors import LlmRateLimitError
from app.containers.container import Container
from app.core.exceptions import AgentOutputError, ModelProviderError
from app.schemas.case_clause import CaseClause
from app.schemas.case_input import CaseInput
from app.schemas.draft import Draft
from app.schemas.eval_case import EvalCase
from tests.evals import baseline as baseline_module
from tests.evals.baseline import Baseline
from tests.evals.eval_results import CaseResult, RunInfo, System, SystemResult
from tests.fakes import InMemoryCaseRepository

CASES_DIR = Path("tests/evals/cases")
RESULTS_DIR = Path("tests/evals/results")
RUN_FILE = "run.json"
# Extra time after a rate limit's stated wait, so the retry lands after the window reopens.
QUOTA_WAIT_MARGIN_SECONDS = 30

logger = logging.getLogger("evals")


class QuotaExhaustedError(Exception):
    """The provider refused for longer than is worth waiting; stop and resume later."""

    def __init__(self, message: str, retry_after_seconds: float | None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


def load_cases(split: str) -> list[EvalCase]:
    return [
        EvalCase.model_validate(json.loads(path.read_text(encoding="utf-8")))
        for path in sorted((CASES_DIR / split).glob("*.json"))
    ]


def case_set_hash(split: str) -> str:
    digest = hashlib.sha256()
    for path in sorted((CASES_DIR / split).glob("*.json")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


def rate_limit_in(error: BaseException) -> LlmRateLimitError | None:
    """The rate limit the client gave up waiting for, if that is what caused the error."""
    cause: BaseException | None = error
    while cause is not None:
        if isinstance(cause, LlmRateLimitError):
            return cause
        cause = cause.__cause__
    return None


def quota_exhausted(error: BaseException) -> bool:
    return rate_limit_in(error) is not None


def stop_for(error: BaseException) -> QuotaExhaustedError:
    limit = rate_limit_in(error)
    return QuotaExhaustedError(
        str(limit or error), limit.retry_after_seconds if limit is not None else None
    )


class Runner:
    def __init__(self, container: Container, run: str) -> None:
        self._container = container
        self._run = run
        services = container.services
        self._workflow = container.agents.case_workflow()
        self._code_check = services.citation_check_service()
        self._baseline = Baseline(
            services.agent_structured_llm(),
            container.utilities.case_renderer(),
            services.rules_engine_service(),
            services.case_retrieval_service(),
        )

    async def graph(self, case: EvalCase) -> SystemResult:
        started = time.perf_counter()
        case_input = self._parse(case)
        if case_input is None:
            return SystemResult(rejected=True)
        case_id = f"{self._run}:{case.case_id}"
        try:
            if await self._workflow.get(case_id) is None:
                state = await self._workflow.start(case_id, case_input, case.as_of_date)
            else:
                # A run that stopped on a rate limit continues from its last saved step,
                # as a retried case does in the application.
                state = await self._workflow.continue_run(case_id)
        except (ModelProviderError, AgentOutputError) as error:
            if quota_exhausted(error):
                raise stop_for(error) from error
            return self._failed(error, started, await self._workflow.get(case_id))
        return self._from_state(state, started)

    async def baseline(self, case: EvalCase) -> SystemResult:
        started = time.perf_counter()
        case_input = self._parse(case)
        if case_input is None:
            return SystemResult(rejected=True)
        clauses = await self._baseline.clauses(case_input, case.as_of_date)
        try:
            result = await self._baseline.run(case_input, case.as_of_date, clauses)
        except (ModelProviderError, AgentOutputError) as error:
            if quota_exhausted(error):
                raise stop_for(error) from error
            return SystemResult(error=str(error), seconds=time.perf_counter() - started)
        call = result.llm_call
        cited, failed = self._citations(result.output, case_input, clauses)
        return SystemResult(
            action=result.output.action,
            reasons=(result.output.summary,),
            citations=cited,
            citations_failed=failed,
            drafts=1,
            model_calls=call.attempts,
            input_tokens=call.input_tokens,
            output_tokens=call.output_tokens,
            latency_ms=call.latency_ms,
            seconds=time.perf_counter() - started,
            draft=result.output,
        )

    def _from_state(self, state: CaseState, started: float) -> SystemResult:
        calls = [event.llm_call for event in state.audit if event.llm_call is not None]
        cited = failed = 0
        if state.draft is not None:
            cited, failed = self._citations(state.draft, state.case_input, state.clauses)
        return SystemResult(
            action=state.triage.action if state.triage else None,
            reasons=state.triage.reasons if state.triage else (),
            verified=state.verification.passed if state.verification else None,
            citations=cited,
            citations_failed=failed,
            drafts=state.writer_attempts,
            model_calls=sum(call.attempts for call in calls),
            input_tokens=sum(call.input_tokens for call in calls),
            output_tokens=sum(call.output_tokens for call in calls),
            latency_ms=sum(call.latency_ms for call in calls),
            seconds=time.perf_counter() - started,
            draft=state.draft,
        )

    def _failed(self, error: Exception, started: float, state: CaseState | None) -> SystemResult:
        partial = self._from_state(state, started) if state is not None else SystemResult()
        return partial.model_copy(update={"error": str(error), "action": None})

    def _citations(
        self, draft: Draft, case_input: CaseInput, clauses: tuple[CaseClause, ...]
    ) -> tuple[int, int]:
        report = self._code_check.check(draft, case_input, clauses)
        cited = sum(len(assertion.citations) for assertion in draft.assertions)
        return cited, sum(len(verdict.problems) for verdict in report.failures())

    @staticmethod
    def _parse(case: EvalCase) -> CaseInput | None:
        try:
            return CaseInput.model_validate(case.input)
        except ValidationError:
            return None


def build_container() -> Container:
    """The application's own wiring, with nothing written to the database."""
    container = Container()
    container.checkpointer.override(providers.Object(InMemorySaver()))
    container.repositories.case_repository.override(providers.Object(InMemoryCaseRepository()))
    return container


def run_info(container: Container, run: str, split: str) -> RunInfo:
    settings = container.settings()
    return RunInfo(
        run=run,
        started_at=datetime.now(UTC),
        split=split,
        case_set=case_set_hash(split),
        agent_model=f"{settings.agent_llm_provider}/{settings.agent_llm_model}",
        judge_model=f"{settings.judge_llm_provider}/{settings.judge_llm_model}",
        prompt_versions={
            "intake": intake_prompt.VERSION,
            "triage": triage_prompt.VERSION,
            "writer": writer_prompt.VERSION,
            "judge": judge_prompt.VERSION,
            "baseline": baseline_module.VERSION,
        },
        retrieval={
            "limit": settings.retrieval_limit,
            "neighbour_sources": settings.retrieval_neighbour_sources,
            "document_additions": settings.retrieval_document_additions,
            "include_visit_note": settings.retrieval_include_visit_note,
        },
    )


async def main(arguments: argparse.Namespace) -> int:
    split = "locked" if arguments.release else "dev"
    run_dir = RESULTS_DIR / arguments.run
    if arguments.fresh and run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    container = build_container()
    info_path = run_dir / RUN_FILE
    info = run_info(container, arguments.run, split)
    if info_path.exists():
        recorded = RunInfo.model_validate_json(info_path.read_text(encoding="utf-8"))
        if recorded.model_dump(exclude={"started_at"}) != info.model_dump(exclude={"started_at"}):
            print(
                "This run was started with different cases, models, prompts or retrieval "
                "settings. Use --fresh to start it over, or --run with a new name."
            )
            return 2
    else:
        info_path.write_text(info.model_dump_json(indent=2) + "\n", encoding="utf-8")

    systems = [System(arguments.only)] if arguments.only else list(System)
    runner = Runner(container, arguments.run)
    done = 0
    try:
        for case in load_cases(split):
            if arguments.cases and case.case_id not in arguments.cases:
                continue
            path = run_dir / f"{case.case_id}.json"
            result = (
                CaseResult.model_validate_json(path.read_text(encoding="utf-8"))
                if path.exists()
                else CaseResult(
                    case_id=case.case_id,
                    scenario=case.scenario,
                    tags=case.tags,
                    expected=case.expected.action,
                    acceptable=case.expected.acceptable_alternatives,
                )
            )
            todo = [system for system in systems if _needs_run(result, system, arguments)]
            if not todo:
                continue
            if arguments.limit is not None and done >= arguments.limit:
                break
            for system in todo:
                outcome = await _run_waiting(runner, case, system, arguments.wait_for_quota)
                result.results[system] = outcome
                # Saved after every system, so a stop loses at most the one in progress.
                path.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")
                print(_progress(case, system, outcome), flush=True)
            done += 1
            if arguments.pause:
                await asyncio.sleep(arguments.pause)
    except QuotaExhaustedError as error:
        print(f"Stopped: the provider's limit is reached ({error}). Run again later to resume.")
        return 3
    finally:
        await container.clients.http_client().aclose()

    remaining = 0
    for case in load_cases(split):
        path = run_dir / f"{case.case_id}.json"
        if not path.exists():
            remaining += 1
            continue
        saved = CaseResult.model_validate_json(path.read_text(encoding="utf-8"))
        remaining += any(_needs_run(saved, system, arguments) for system in systems)
    print(f"Cases run this time: {done}. Cases still to run: {remaining}.")
    return 0


def _needs_run(result: CaseResult, system: System, arguments: argparse.Namespace) -> bool:
    """Not run yet, or run and stopped on an error that --retry-errors asks to repeat."""
    outcome = result.results.get(system)
    return outcome is None or (arguments.retry_errors and outcome.error is not None)


async def _run_waiting(
    runner: Runner, case: EvalCase, system: System, wait_for_quota_minutes: float
) -> SystemResult:
    """Run one system on one case, sleeping through a rate limit when allowed to.

    Groq's daily token limit is a rolling window, so tokens come free again over time;
    the provider says how long to wait. Without --wait-for-quota, or when the wait asked
    for is longer than allowed, the limit stops the run so it can be resumed later.
    """
    while True:
        try:
            if system is System.GRAPH:
                return await runner.graph(case)
            return await runner.baseline(case)
        except QuotaExhaustedError as error:
            wait = error.retry_after_seconds
            if wait is None or wait > wait_for_quota_minutes * 60:
                raise
            print(f"Rate limit reached; waiting {wait / 60:.1f} min before retrying.", flush=True)
            await asyncio.sleep(wait + QUOTA_WAIT_MARGIN_SECONDS)


def _progress(case: EvalCase, system: System, outcome: SystemResult) -> str:
    expected = case.expected.action.value if case.expected.action else "REJECT"
    got = (
        "REJECT"
        if outcome.rejected
        else (outcome.action.value if outcome.action else f"ERROR {outcome.error}")
    )
    mark = (
        "ok"
        if got == expected or any(got == a.value for a in case.expected.acceptable_alternatives)
        else "--"
    )
    return (
        f"{case.case_id:9} {system.value:8} {mark} expected {expected:22} got {got:22} "
        f"{outcome.input_tokens + outcome.output_tokens:6} tokens {outcome.seconds:5.0f} s"
    )


def parse(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the evaluation cases.")
    parser.add_argument("--run", default="dev", help="name of the run (a results folder)")
    parser.add_argument("--limit", type=int, help="run at most this many cases this time")
    parser.add_argument("--pause", type=float, default=0.0, help="seconds between cases")
    parser.add_argument("--only", choices=[system.value for system in System])
    parser.add_argument(
        "--case",
        action="append",
        dest="cases",
        metavar="CASE_ID",
        help="run only this case; repeat for several",
    )
    parser.add_argument("--fresh", action="store_true", help="discard the run and start over")
    parser.add_argument("--release", action="store_true", help="run the locked cases")
    parser.add_argument(
        "--retry-errors", action="store_true", help="run again results that stopped on an error"
    )
    parser.add_argument(
        "--wait-for-quota",
        type=float,
        default=0.0,
        metavar="MINUTES",
        help="sleep through a rate limit asking for at most this long, instead of stopping",
    )
    return parser.parse_args(argv)


def entrypoint() -> int:
    logging.basicConfig(level=logging.ERROR, stream=sys.stderr)
    arguments = parse()
    # The PostgreSQL driver is not used here, but the app's import paths expect this loop.
    loop_factory: Any = asyncio.SelectorEventLoop if sys.platform == "win32" else None
    return asyncio.run(main(arguments), loop_factory=loop_factory)


if __name__ == "__main__":
    sys.exit(entrypoint())
