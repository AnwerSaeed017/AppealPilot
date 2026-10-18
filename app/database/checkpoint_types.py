import importlib
import pkgutil
from enum import Enum
from types import ModuleType

from pydantic import BaseModel

import app.agents.states
import app.schemas

# The packages whose classes make up a case's workflow state.
_STATE_PACKAGES: tuple[ModuleType, ...] = (app.schemas, app.agents.states)


def checkpoint_types() -> tuple[tuple[str, str], ...]:
    """Every class the workflow engine may rebuild when it loads saved state.

    Loading is restricted to this list, as (module, class name) pairs. Anything else
    found in a checkpoint is refused, so stored data cannot make the application
    construct an arbitrary class.
    """
    found: set[tuple[str, str]] = set()
    for package in _STATE_PACKAGES:
        for module_info in pkgutil.iter_modules(package.__path__, f"{package.__name__}."):
            module = importlib.import_module(module_info.name)
            for name, value in vars(module).items():
                is_state_class = isinstance(value, type) and issubclass(value, BaseModel | Enum)
                if is_state_class and value.__module__ == module.__name__:
                    found.add((module.__name__, name))
    return tuple(sorted(found))
