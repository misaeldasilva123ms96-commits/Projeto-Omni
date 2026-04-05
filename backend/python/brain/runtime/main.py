from __future__ import annotations

import sys
from pathlib import Path

from brain.runtime.orchestrator import BrainOrchestrator, BrainPaths


def run_cli(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    message = args[0] if args else ""
    orchestrator = BrainOrchestrator(BrainPaths.from_entrypoint(Path(__file__)))
    response = orchestrator.run(message)
    try:
        print(response)
    except UnicodeEncodeError:
        sys.stdout.buffer.write(f"{response}\n".encode("utf-8", errors="replace"))
    return 0
