"""Write the API's OpenAPI document, which the web client's types are generated from.

    uv run python -m scripts.export_openapi
    (cd web && npm run api:types)

Run both after changing an endpoint or a schema the API returns, and commit the result,
so the web build never depends on a running backend.
"""

import json
import sys
from pathlib import Path

from app.main import app

DEFAULT_TARGET = Path("web/openapi.json")


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_TARGET
    document = json.dumps(app.openapi(), indent=2, sort_keys=True)
    target.write_text(f"{document}\n", encoding="utf-8")
    print(f"wrote {target}")


if __name__ == "__main__":
    main()
