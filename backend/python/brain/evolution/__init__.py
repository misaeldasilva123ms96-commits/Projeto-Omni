from __future__ import annotations

from pathlib import Path

from brain.env import read_env
from brain.evolution.evolution_loop import start_evolution_loop


def boot_evolution_loop() -> None:
    if read_env("OMNI_DISABLE_EVOLUTION_LOOP").lower() in {"1", "true", "yes"}:
        return

    configured_python_root = read_env("OMNI_PYTHON_BASE_DIR")
    python_root = Path(configured_python_root).resolve() if configured_python_root else Path(__file__).resolve().parents[2]
    start_evolution_loop(python_root)


__all__ = ["boot_evolution_loop", "start_evolution_loop"]
