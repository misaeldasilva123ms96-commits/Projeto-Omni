from __future__ import annotations

import sys
from pathlib import Path

from brain.runtime.bridge_stdin import apply_bridge_env, resolve_entry_message
from brain.runtime.orchestrator import BrainOrchestrator, BrainPaths


def run_cli(argv: list[str] | None = None) -> int:
    if argv is not None:
        message = argv[0] if argv else ""
        apply_bridge_env({})
    else:
        message, bridge = resolve_entry_message()
        apply_bridge_env(bridge)
    orchestrator = BrainOrchestrator(BrainPaths.from_entrypoint(Path(__file__)))
    response = orchestrator.run(message)
    try:
        print(response)
    except UnicodeEncodeError:
        sys.stdout.buffer.write(f"{response}\n".encode("utf-8", errors="replace"))
    return 0
