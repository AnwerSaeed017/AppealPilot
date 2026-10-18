import asyncio
from collections.abc import Coroutine
from typing import Any

from app.interfaces.utilities.task_runner import ITaskRunner


class AsyncTaskRunner(ITaskRunner):
    """Background work as asyncio tasks on the running event loop.

    It keeps a reference to each task until it finishes; without one, the event loop
    may discard a task that is still running.
    """

    def __init__(self) -> None:
        self._tasks: set[asyncio.Task[None]] = set()

    def start(self, work: Coroutine[Any, Any, None]) -> None:
        task = asyncio.get_running_loop().create_task(work)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def drain(self) -> None:
        while self._tasks:
            await asyncio.gather(*tuple(self._tasks), return_exceptions=True)

    async def cancel_all(self) -> None:
        tasks = tuple(self._tasks)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
