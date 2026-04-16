from __future__ import annotations

import json
import shutil
import sys
import unittest
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.control import (  # noqa: E402
    FileSystemRunRegistryBackend,
    InMemoryRunRegistryBackend,
    RunRecord,
    RunRegistry,
    RunStatus,
)


class FileSystemRunRegistryBackendTest(unittest.TestCase):
    def setUp(self) -> None:
        base = PROJECT_ROOT / ".logs" / "test-run-registry-backend"
        base.mkdir(parents=True, exist_ok=True)
        self._workspace = base / f"ws-{uuid4().hex[:8]}"
        self._workspace.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self._workspace, ignore_errors=True)

    def test_load_save_roundtrip_and_metadata(self) -> None:
        backend = FileSystemRunRegistryBackend(self._workspace)
        self.assertEqual(backend.metadata().backend_id, "filesystem")
        self.assertTrue(str(backend.metadata().storage_path or "").endswith("run_registry.json"))
        doc = {"runs": {"r1": {"run_id": "r1", "goal_id": None, "session_id": "s", "status": "running", "started_at": "2024-01-01T00:00:00+00:00", "updated_at": "2024-01-01T00:00:00+00:00", "last_action": "x", "progress_score": 0.0, "metadata": {}, "resolution": {"current_resolution": "running", "previous_resolution": "running", "reason": "x", "decision_source": "runtime_orchestrator", "timestamp": "2024-01-01T00:00:00+00:00"}, "resolution_history": [], "governance_timeline": []}}}
        backend.save(doc)
        self.assertTrue(backend.exists())
        loaded = backend.load()
        self.assertEqual(loaded["runs"]["r1"]["run_id"], "r1")

    def test_atomic_write_leaves_no_tmp_stale(self) -> None:
        backend = FileSystemRunRegistryBackend(self._workspace)
        backend.save({"runs": {}})
        tmp_files = list(backend.control_dir.glob("run_registry*.tmp"))
        self.assertEqual(tmp_files, [])

    def test_invalid_json_raises_value_error(self) -> None:
        backend = FileSystemRunRegistryBackend(self._workspace)
        backend.registry_path.write_text("{not json", encoding="utf-8")
        with self.assertRaises(ValueError):
            backend.load()


class InMemoryRunRegistryBackendTest(unittest.TestCase):
    def test_registry_with_memory_backend_round_trip(self) -> None:
        root = PROJECT_ROOT / ".logs" / "test-run-registry-mem"
        root.mkdir(parents=True, exist_ok=True)
        mem = InMemoryRunRegistryBackend()
        reg = RunRegistry(root, backend=mem)
        self.assertEqual(reg.persistence_backend.metadata().backend_id, "memory")
        reg.register(
            RunRecord.build(
                run_id="mem-run",
                goal_id=None,
                session_id="s-mem",
                status=RunStatus.RUNNING,
                last_action="execution_started",
                progress_score=0.0,
            )
        )
        self.assertTrue(mem.exists())
        reg2 = RunRegistry(root, backend=mem)
        loaded = reg2.get("mem-run")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.status, RunStatus.RUNNING)


class RunRegistryDefaultBackendTest(unittest.TestCase):
    def setUp(self) -> None:
        base = PROJECT_ROOT / ".logs" / "test-run-registry-default"
        base.mkdir(parents=True, exist_ok=True)
        self._workspace = base / f"ws-{uuid4().hex[:8]}"
        self._workspace.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self._workspace, ignore_errors=True)

    def test_default_backend_matches_filesystem_layout(self) -> None:
        reg = RunRegistry(self._workspace)
        self.assertEqual(reg.persistence_backend.metadata().backend_id, "filesystem")
        expected = self._workspace / ".logs" / "fusion-runtime" / "control" / "run_registry.json"
        self.assertEqual(reg.path.resolve(), expected.resolve())


class LegacyJsonLoadTest(unittest.TestCase):
    def setUp(self) -> None:
        base = PROJECT_ROOT / ".logs" / "test-run-registry-legacy"
        base.mkdir(parents=True, exist_ok=True)
        self._workspace = base / f"ws-{uuid4().hex[:8]}"
        self._workspace.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self._workspace, ignore_errors=True)

    def test_manual_disk_json_loads_via_default_registry(self) -> None:
        ctrl = self._workspace / ".logs" / "fusion-runtime" / "control"
        ctrl.mkdir(parents=True, exist_ok=True)
        path = ctrl / "run_registry.json"
        payload = {
            "runs": {
                "legacy_x": {
                    "run_id": "legacy_x",
                    "goal_id": None,
                    "session_id": "s",
                    "status": "running",
                    "started_at": "2024-01-01T00:00:00+00:00",
                    "updated_at": "2024-01-01T00:00:00+00:00",
                    "last_action": "execution_started",
                    "progress_score": 0.0,
                    "metadata": {},
                    "resolution": {
                        "current_resolution": "running",
                        "previous_resolution": "running",
                        "reason": "execution_started",
                        "decision_source": "runtime_orchestrator",
                        "timestamp": "2024-01-01T00:00:00+00:00",
                    },
                    "resolution_history": [],
                    "governance_timeline": [],
                }
            }
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        reg = RunRegistry(self._workspace)
        rec = reg.get("legacy_x")
        self.assertIsNotNone(rec)
        self.assertEqual(rec.run_id, "legacy_x")


if __name__ == "__main__":
    unittest.main()
