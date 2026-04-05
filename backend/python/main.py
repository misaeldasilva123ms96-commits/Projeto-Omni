from __future__ import annotations

import os
from pathlib import Path

from brain.runtime.main import run_cli


def main() -> int:
    python_root = Path(__file__).resolve().parent
    project_root = python_root.parents[1]
    os.environ.setdefault("PYTHON_BASE_DIR", str(python_root))
    os.environ.setdefault("BASE_DIR", str(project_root))
    return run_cli()


if __name__ == "__main__":
    raise SystemExit(main())
