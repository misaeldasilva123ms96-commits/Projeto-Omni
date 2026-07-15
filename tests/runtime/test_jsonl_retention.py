from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.orchestrator import (  # noqa: E402
    BrainOrchestrator,
    _JSONL_PREPARED_PATHS,
)


def test_jsonl_sanitization_runs_once_per_active_file(tmp_path: Path) -> None:
    path = tmp_path / "runtime.jsonl"
    path.write_text('{"valid":true}\nnot-json\n', encoding="utf-8")
    _JSONL_PREPARED_PATHS.discard(path.resolve())

    with patch.object(
        BrainOrchestrator,
        "_sanitize_jsonl_file",
        wraps=BrainOrchestrator._sanitize_jsonl_file,
    ) as sanitize:
        BrainOrchestrator._append_jsonl(path, {"sequence": 1})
        BrainOrchestrator._append_jsonl(path, {"sequence": 2})

    assert sanitize.call_count == 1
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines == ['{"valid":true}', '{"sequence": 1}', '{"sequence": 2}']


def test_jsonl_archive_retention_prunes_count_and_age(
    tmp_path: Path,
    monkeypatch,
) -> None:
    path = tmp_path / "runtime.jsonl"
    now = time.time()
    archives = []
    for index in range(6):
        archive = tmp_path / f"runtime.jsonl.20260714T12000{index}.bak"
        archive.write_text("{}\n", encoding="utf-8")
        os.utime(archive, (now - (index * 86_400), now - (index * 86_400)))
        archives.append(archive)

    monkeypatch.setenv("OMNI_JSONL_ARCHIVE_RETENTION_COUNT", "3")
    monkeypatch.setenv("OMNI_JSONL_ARCHIVE_RETENTION_DAYS", "2")
    BrainOrchestrator._prune_jsonl_archives(path)

    remaining = sorted(tmp_path.glob("runtime.jsonl.*.bak"))
    assert len(remaining) == 2
    assert set(remaining) == set(archives[:2])
