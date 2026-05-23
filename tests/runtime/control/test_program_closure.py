"""
Phase 30.9 — integrated closure checks for OIL + governance control plane (30.1–30.9).
"""

from __future__ import annotations

import json
import shutil
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

import brain.runtime.control as control_pkg  # noqa: E402
import brain.runtime.language as language_pkg  # noqa: E402
from brain.runtime.control.governance_read_model import build_operational_governance_snapshot  # noqa: E402
from brain.runtime.control.program_closure import (  # noqa: E402
    OMNI_RUNTIME_CONVERGENCE_PHASE,
    OMNI_RUNTIME_CONVERGENCE_PROGRAM,
    assert_operational_governance_contract,
    empty_operational_governance_fallback,
    empty_resolution_summary_fallback,
    validate_operational_governance_shape,
)
from brain.runtime.control.run_registry import RunRegistry, RunStatus  # noqa: E402
from brain.runtime.observability.observability_reader import ObservabilityReader  # noqa: E402
from brain.runtime.observability.run_reader import read_operational_governance, read_resolution_summary  # noqa: E402


class ProgramClosureTest(unittest.TestCase):
    @contextmanager
    def temp_workspace(self):
        base = PROJECT_ROOT / ".logs" / "test-program-closure"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"closure-{uuid4().hex[:8]}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def test_oil_and_control_exports_stable(self) -> None:
        self.assertIn("OMNI_OIL_PROGRAM_RANGE", language_pkg.__all__)
        self.assertEqual(language_pkg.OMNI_OIL_PROGRAM_RANGE, "30.1-30.9")
        for name in (
            "GovernanceResolutionController",
            "build_operational_governance_snapshot",
            "GOVERNANCE_TAXONOMY_VERSION",
            "OMNI_RUNTIME_CONVERGENCE_PROGRAM",
            "validate_operational_governance_shape",
        ):
            self.assertIn(name, control_pkg.__all__)
            self.assertTrue(hasattr(control_pkg, name))

    def test_operational_snapshot_contract(self) -> None:
        with self.temp_workspace() as root:
            reg = RunRegistry(root)
            snap = build_operational_governance_snapshot(reg)
            assert_operational_governance_contract(snap)
            self.assertEqual([], validate_operational_governance_shape(snap))

    def test_empty_fallbacks_match_contract(self) -> None:
        r = empty_resolution_summary_fallback()
        self.assertIn("governance", r)
        self.assertEqual(r["governance"]["taxonomy_version"], control_pkg.GOVERNANCE_TAXONOMY_VERSION)
        o = empty_operational_governance_fallback()
        assert_operational_governance_contract(o)
        o2 = empty_operational_governance_fallback(summary=r)
        assert_operational_governance_contract(o2)

    def test_legacy_run_readable_and_snapshot_coherent(self) -> None:
        with self.temp_workspace() as root:
            control_dir = root / ".logs" / "fusion-runtime" / "control"
            control_dir.mkdir(parents=True, exist_ok=True)
            legacy = {
                "runs": {
                    "legacy-closure": {
                        "run_id": "legacy-closure",
                        "goal_id": None,
                        "session_id": "s1",
                        "status": "running",
                        "started_at": "2026-01-01T00:00:00+00:00",
                        "updated_at": "2026-01-02T00:00:00+00:00",
                        "last_action": "execution_started",
                        "progress_score": 0.1,
                        "metadata": {},
                        "resolution": {
                            "current_resolution": "running",
                            "previous_resolution": "running",
                            "reason": "running",
                            "decision_source": "runtime_orchestrator",
                            "timestamp": "2026-01-02T00:00:00+00:00",
                        },
                        "resolution_history": [],
                    }
                }
            }
            (control_dir / "run_registry.json").write_text(
                json.dumps(legacy, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            og = read_operational_governance(root)
            assert_operational_governance_contract(og)
            self.assertGreaterEqual(og["total_runs"], 1)
            rs = read_resolution_summary(root)
            self.assertIn("governance", rs)

    def test_observability_operational_governance_field(self) -> None:
        with self.temp_workspace() as root:
            control_dir = root / ".logs" / "fusion-runtime" / "control"
            control_dir.mkdir(parents=True, exist_ok=True)
            (control_dir / "run_registry.json").write_text(
                json.dumps({"runs": {}}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            snap = ObservabilityReader(root).snapshot()
            assert_operational_governance_contract(snap.operational_governance)

    def test_controller_registry_timeline_alignment(self) -> None:
        with self.temp_workspace() as root:
            reg = RunRegistry(root)
            ctrl = control_pkg.GovernanceResolutionController(reg)
            ctrl.register_run_start(
                run_id="align-1",
                goal_id=None,
                session_id="s1",
                status=RunStatus.RUNNING,
                last_action="execution_started",
                progress_score=0.0,
            )
            ctrl.transition_run(
                run_id="align-1",
                status=RunStatus.PAUSED,
                last_action="operator_pause",
                progress=0.2,
                reason="operator_pause",
                decision_source="operator_cli",
                operator_id="op",
            )
            rec = reg.get("align-1")
            self.assertIsNotNone(rec)
            self.assertGreaterEqual(len(rec.governance_timeline), 2)
            snap = build_operational_governance_snapshot(reg)
            assert_operational_governance_contract(snap)
            w = [r for r in snap["waiting_operator_runs"] if r["run_id"] == "align-1"]
            self.assertEqual(len(w), 1)

    def test_program_constants(self) -> None:
        self.assertEqual(OMNI_RUNTIME_CONVERGENCE_PROGRAM, "30.1-30.9")
        self.assertEqual(OMNI_RUNTIME_CONVERGENCE_PHASE, "30.9")


if __name__ == "__main__":
    unittest.main()
