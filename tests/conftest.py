import asyncio
import os
import sys
from collections.abc import Callable, Mapping

import pytest

# Settings are read when app.main is imported, so pin them before any test imports it.
# Environment variables take priority over a developer's env/.env.
os.environ.update(
    {
        "ENVIRONMENT": "test",
        "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
        "AGENT_LLM_PROVIDER": "mock",
        "JUDGE_LLM_PROVIDER": "mock",
    }
)


def pytest_asyncio_loop_factories(
    config: pytest.Config, item: pytest.Item
) -> Mapping[str, Callable[[], asyncio.AbstractEventLoop]] | None:
    """The PostgreSQL driver cannot run on Windows' default event loop."""
    if sys.platform == "win32":
        return {"selector": asyncio.SelectorEventLoop}
    return None
