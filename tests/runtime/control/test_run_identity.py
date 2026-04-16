from __future__ import annotations

import io
import json
import shutil
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.control import RunRecord, RunRegistry, RunStatus  # noqa: E402
from brain.runtime.control.cli import main as control_cli_main  # noqa: E402
from brain.runtime.control.run_identity import (  # noqa: E402
    RUN_ID_MAX_LEN,
    coerce_runtime_run_id,
    normalize_run_id,
    run_id_lookup_keys,
    validate_run_id_for_new_write,
    validate_run_id_for_operator_cli,
)
from brain.runtime.observability.run_reader import read_run  # noqa: E402


class RunIdentityTest(unittest.TestCase):
    def test_normalize_run_id_trims_only(self) -> None:
        self.assertEqual(normalize_run_id("  Ab-1_  "), "Ab-1_")

    def test_validate_run_id_for_new_write_accepts_alphanumeric_hyphen_underscore(self) -> None:
        self.assertEqual(validate_run_id_for_new_write("run-1_ok"), "run-1_ok")

    def test_validate_run_id_for_new_write_rejects_empty(self) -> None:
        with self.assertRaises(ValueError):
            validate_run_id_for_new_write("")
        with self.assertRaises(ValueError):
            validate_run_id_for_new_write("   ")

    def test_validate_run_id_for_new_write_rejects_too_long(self) -> None:
        with self.assertRaises(ValueError):
            validate_run_id_for_new_write("a" * (RUN_ID_MAX_LEN + 1))

    def test_validate_run_id_for_new_write_rejects_path_traversal(self) -> None:
        for bad in ("../x", "x/../y", "a/b", r"a\b", "a..b"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    validate_run_id_for_new_write(bad)

    def test_validate_run_id_for_new_write_rejects_invalid_characters(self) -> None:
        for bad in ("run id", "run@id", "run.id", "run:id"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    validate_run_id_for_new_write(bad)

    def test_run_id_lookup_keys_valid_returns_single_canonical(self) -> None:
        self.assertEqual(run_id_lookup_keys("  Run-Ab_1  "), ("Run-Ab_1",))

    def test_run_id_lookup_keys_legacy_returns_raw_only(self) -> None:
        self.assertEqual(run_id_lookup_keys("weird:id"), ("weird:id",))

    def test_validate_run_id_for_operator_cli_allows_legacy_punctuation(self) -> None:
        self.assertEqual(validate_run_id_for_operator_cli("weird:id"), "weird:id")

    def test_validate_run_id_for_operator_cli_rejects_path_patterns(self) -> None:
        with self.assertRaises(ValueError):
            validate_run_id_for_operator_cli("../nope")

    def test_coerce_runtime_run_id_valid_passthrough(self) -> None:
        self.assertEqual(
            coerce_runtime_run_id(run_id="run-fixed", session_id="any"),
            "run-fixed",
        )

    def test_coerce_runtime_run_id_fallback_from_session(self) -> None:
        self.assertEqual(
            coerce_runtime_run_id(run_id="../../bad", session_id="sess-1"),
            "run-sess-1",
        )

    def test_run_record_build_rejects_invalid_new_run_id(self) -> None:
        with self.assertRaises(ValueError):
            RunRecord.build(
                run_id="bad/run",
                goal_id=None,
                session_id="s",
                status=RunStatus.RUNNING,
                last_action="x",
                progress_score=0.0,
            )

    def test_legacy_registry_disk_key_still_readable(self) -> None:
        base = PROJECT_ROOT / ".logs" / "test-run-identity-legacy"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"legacy-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            ctrl = path / ".logs" / "fusion-runtime" / "control"
            ctrl.mkdir(parents=True, exist_ok=True)
            reg_path = ctrl / "run_registry.json"
            payload = {
                "runs": {
                    "weird:id": {
                        "run_id": "weird:id",
                        "goal_id": None,
                        "session_id": "s1",
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
            reg_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            registry = RunRegistry(path)
            loaded = registry.get("weird:id")
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.run_id, "weird:id")
            snapshot = read_run(path, "weird:id")
            self.assertIsNotNone(snapshot)
            self.assertEqual(snapshot.get("run_id"), "weird:id")
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def test_control_cli_rejects_invalid_operator_run_id(self) -> None:
        base = PROJECT_ROOT / ".logs" / "test-run-identity-cli"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"cli-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            stream = io.StringIO()
            with patch.object(
                sys,
                "argv",
                ["control-cli", "--root", str(path), "pause", "../escape"],
            ):
                with redirect_stdout(stream):
                    result = control_cli_main()
            self.assertEqual(result, 0)
            payload = json.loads(stream.getvalue())
            self.assertEqual(payload["status"], "error")
            self.assertEqual(payload["error"], "invalid_run_id")
            self.assertIn("message", payload)
        finally:
            shutil.rmtree(path, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
