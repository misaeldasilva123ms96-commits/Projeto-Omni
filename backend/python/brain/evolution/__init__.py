from __future__ import annotations

import os
from pathlib import Path

from brain.evolution.evolution_loop import start_evolution_loop


def boot_evolution_loop() -> None:
    if os.getenv("OMINI_DISABLE_EVOLUTION_LOOP", "").strip().lower() in {"1", "true", "yes"}:
        return

    python_root = (
        Path(os.environ["PYTHON_BASE_DIR"]).resolve()
        if os.getenv("PYTHON_BASE_DIR")
        else Path(__file__).resolve().parents[2]
    )
    start_evolution_loop(python_root)


__all__ = ["boot_evolution_loop", "start_evolution_loop"]
