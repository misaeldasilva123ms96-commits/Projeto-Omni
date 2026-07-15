from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.orchestrator import BrainOrchestrator, _JSONL_PREPARED_PATHS  # noqa: E402


@pytest.mark.parametrize(
    ("target_bytes", "soft_ceiling_seconds"),
    [
        (10 * 1024 * 1024 - 256, 15.0),
        (50 * 1024 * 1024 + 256, 8.0),
    ],
)
def test_jsonl_append_is_bounded_near_operational_thresholds(
    tmp_path: Path,
    target_bytes: int,
    soft_ceiling_seconds: float,
) -> None:
    path = tmp_path / "runtime.jsonl"
    row = b'{"benchmark":true}\n'
    repetitions, remainder = divmod(target_bytes, len(row))
    with path.open("wb") as handle:
        for _ in range(repetitions):
            handle.write(row)
        if remainder:
            handle.write(row[:remainder])
    _JSONL_PREPARED_PATHS.discard(path.resolve())

    started = time.monotonic()
    BrainOrchestrator._append_jsonl(path, {"benchmark_append": True})
    elapsed = time.monotonic() - started

    assert elapsed < soft_ceiling_seconds
    if target_bytes > 50 * 1024 * 1024:
        assert list(tmp_path.glob("runtime.jsonl.*.bak"))
