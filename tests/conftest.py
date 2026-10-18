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


if sys.platform == "win32":
    # Defined only on Windows: elsewhere pytest-asyncio's default loop is right, and the
    # hook must not return an empty answer.
    def pytest_asyncio_loop_factories(
        config: pytest.Config, item: pytest.Item
    ) -> Mapping[str, Callable[[], asyncio.AbstractEventLoop]]:
        """The PostgreSQL driver cannot run on Windows' default event loop."""
        return {"selector": asyncio.SelectorEventLoop}
