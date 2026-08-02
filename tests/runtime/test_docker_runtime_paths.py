from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.orchestrator import BrainPaths  # noqa: E402


def test_brain_paths_honor_writable_runtime_overrides(monkeypatch) -> None:
    swarm_log = Path("/tmp/omni-smoke/swarm.json")
    evolution_dir = Path("/tmp/omni-smoke/evolution")
    monkeypatch.setenv("OMNI_SWARM_LOG_PATH", str(swarm_log))
    monkeypatch.setenv("OMNI_EVOLUTION_DIR", str(evolution_dir))

    paths = BrainPaths.from_entrypoint(PROJECT_ROOT / "backend" / "python" / "main.py")

    assert paths.swarm_log == swarm_log
    assert paths.evolution_dir == evolution_dir


def test_brain_paths_keep_canonical_defaults(monkeypatch) -> None:
    monkeypatch.delenv("OMNI_SWARM_LOG_PATH", raising=False)
    monkeypatch.delenv("OMNI_EVOLUTION_DIR", raising=False)

    paths = BrainPaths.from_entrypoint(PROJECT_ROOT / "backend" / "python" / "main.py")

    assert paths.swarm_log == paths.python_root / "brain" / "runtime" / "swarm_log.json"
    assert paths.evolution_dir == paths.python_root / "brain" / "evolution"
