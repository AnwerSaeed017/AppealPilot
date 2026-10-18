"""Rebuild the generated evaluation cases and the planted-error drafts.

python -m tests.evals.generator            write the files
python -m tests.evals.generator --check    fail if the files on disk are out of date
"""

import argparse
import sys
from pathlib import Path

from tests.evals.generator.build import (
    DEFAULT_SEED,
    build_cases,
    render_files,
    stale_files,
    write_files,
)
from tests.evals.generator.planted import (
    build_planted,
    render_planted_files,
    write_planted_files,
)

DEFAULT_CASES_DIR = Path("tests/evals/cases")
DEFAULT_PLANTED_DIR = Path("tests/evals/planted")


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--out", type=Path, default=DEFAULT_CASES_DIR)
    parser.add_argument("--planted-out", type=Path, default=DEFAULT_PLANTED_DIR)
    parser.add_argument("--check", action="store_true", help="compare with disk; write nothing")
    arguments = parser.parse_args()

    cases = build_cases(arguments.seed)
    case_files = render_files(cases)
    planted = build_planted(cases, arguments.seed)
    planted_files = render_planted_files(planted)

    if arguments.check:
        stale = stale_files(case_files, arguments.out) + stale_files(
            planted_files, arguments.planted_out
        )
        if stale:
            print(f"{len(stale)} generated files are out of date:")
            for path in stale:
                print(f"  {path}")
            return 1
        print(f"{len(cases)} cases and {len(planted)} planted drafts are up to date.")
        return 0

    write_files(case_files, arguments.out)
    write_planted_files(planted_files, arguments.planted_out)
    print(f"Wrote {len(cases)} cases to {arguments.out}.")
    print(f"Wrote {len(planted)} planted drafts to {arguments.planted_out}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
