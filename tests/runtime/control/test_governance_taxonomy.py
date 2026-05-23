from __future__ import annotations

import io
import json
import shutil
import sys
import unittest
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.control import (  # noqa: E402
    GovernanceReason,
    GovernanceSeverity,
    GovernanceSource,
    RunRecord,
    RunRegistry,
    RunStatus,
    build_governance_decision,
    infer_governance_reason,
    map_action_to_reason,
    map_legacy_reason_string,
    normalize_governance_source,
)
from brain.runtime.control.cli import main as control_cli_main  # noqa: E402
from brain.runtime.observability.observability_reader import ObservabilityReader  # noqa: E402


class GovernanceTaxonomyTest(unittest.TestCase):
    def test_reason_normalization_enum(self) -> None:
        self.assertEqual(map_legacy_reason_string("policy_block").value, "policy_block")
        self.assertEqual(map_legacy_reason_string("unknown", fallback=GovernanceReason.TIMEOUT), GovernanceReason.TIMEOUT)

    def test_source_normalization(self) -> None:
        self.assertEqual(normalize_governance_source("operator_cli"), GovernanceSource.OPERATOR)
        self.assertEqual(normalize_governance_source("runtime_orchestrator"), GovernanceSource.RUNTIME)

    def test_severity_consistent(self) -> None:
        d = build_governance_decision(reason="policy_block", decision_source="runtime_orchestrator")
        self.assertEqual(d.severity, GovernanceSeverity.CRITICAL)
        d2 = build_governance_decision(reason="operator_pause", decision_source="operator_cli")
        self.assertEqual(d2.severity, GovernanceSeverity.MANUAL)

    def test_mapping_deterministic(self) -> None:
        a = map_action_to_reason("governance_hold", run_status="running")
        b = map_action_to_reason("governance_hold", run_status="running")
        self.assertEqual(a, b)
        self.assertEqual(
            infer_governance_reason(last_action="pause_plan", run_status="paused"),
            GovernanceReason.OPERATOR_PAUSE,
        )

    def test_run_registry_resolution_includes_governance(self) -> None:
        @contextmanager
        def temp_workspace():
            base = PROJECT_ROOT / ".logs" / "test-governance-taxonomy"
            base.mkdir(parents=True, exist_ok=True)
            path = base / f"gov-{uuid4().hex[:8]}"
            path.mkdir(parents=True, exist_ok=True)
            try:
                yield path
            finally:
                shutil.rmtree(path, ignore_errors=True)

        with temp_workspace() as workspace_root:
            registry = RunRegistry(workspace_root)
            registry.register(
                RunRecord.build(
                    run_id="run-g",
                    goal_id=None,
                    session_id="s1",
                    status=RunStatus.RUNNING,
                    last_action="execution_started",
                    progress_score=0.0,
                )
            )
            registry.update_status(
                "run-g",
                RunStatus.PAUSED,
                "operator_pause",
                0.2,
                reason="operator_pause",
                decision_source="operator_cli",
            )
            stored = registry.get("run-g")
            self.assertIsNotNone(stored)
            self.assertIsNotNone(stored.resolution)
            d = stored.resolution.as_dict()
            self.assertIn("governance", d)
            self.assertEqual(d["governance"]["reason"], "operator_pause")
            self.assertEqual(d["governance"]["source"], "operator")
            self.assertEqual(d["governance"]["severity"], "manual")

    def test_resolution_summary_governance_block(self) -> None:
        @contextmanager
        def temp_workspace():
            base = PROJECT_ROOT / ".logs" / "test-governance-summary"
            base.mkdir(parents=True, exist_ok=True)
            path = base / f"gsum-{uuid4().hex[:8]}"
            path.mkdir(parents=True, exist_ok=True)
            try:
                yield path
            finally:
                shutil.rmtree(path, ignore_errors=True)

        with temp_workspace() as workspace_root:
            registry = RunRegistry(workspace_root)
            registry.register(
                RunRecord.build(
                    run_id="run-p",
                    goal_id=None,
                    session_id="s1",
                    status=RunStatus.FAILED,
                    last_action="policy_block",
                    progress_score=0.0,
                )
            )
            summary = registry.get_resolution_summary()
            self.assertIn("governance", summary)
            self.assertGreaterEqual(summary["governance"]["blocked_by_policy"], 1)

    def test_observability_policy_block_uses_governance(self) -> None:
        @contextmanager
        def temp_workspace():
            base = PROJECT_ROOT / ".logs" / "test-obs-gov"
            base.mkdir(parents=True, exist_ok=True)
            path = base / f"obs-{uuid4().hex[:8]}"
            path.mkdir(parents=True, exist_ok=True)
            try:
                yield path
            finally:
                shutil.rmtree(path, ignore_errors=True)

        with temp_workspace() as workspace_root:
            registry = RunRegistry(workspace_root)
            registry.register(
                RunRecord.build(
                    run_id="run-pol",
                    goal_id=None,
                    session_id="s1",
                    status=RunStatus.FAILED,
                    last_action="policy_block",
                    progress_score=0.0,
                )
            )
            snap = ObservabilityReader(workspace_root).snapshot()
            self.assertTrue(len(snap.runs_blocked_by_policy) >= 1)

    def test_cli_show_includes_governance(self) -> None:
        @contextmanager
        def temp_workspace():
            base = PROJECT_ROOT / ".logs" / "test-cli-gov"
            base.mkdir(parents=True, exist_ok=True)
            path = base / f"cli-{uuid4().hex[:8]}"
            path.mkdir(parents=True, exist_ok=True)
            try:
                yield path
            finally:
                shutil.rmtree(path, ignore_errors=True)

        with temp_workspace() as workspace_root:
            registry = RunRegistry(workspace_root)
            registry.register(
                RunRecord.build(
                    run_id="run-cli-g",
                    goal_id=None,
                    session_id="s1",
                    status=RunStatus.RUNNING,
                    last_action="start",
                    progress_score=0.5,
                )
            )
            stream = io.StringIO()
            with patch.object(sys, "argv", ["control-cli", "--root", str(workspace_root), "show", "run-cli-g"]):
                with redirect_stdout(stream):
                    control_cli_main()
            payload = json.loads(stream.getvalue())
            gov = payload["run"]["resolution"]["governance"]
            self.assertEqual(set(gov.keys()), {"reason", "source", "severity"})


if __name__ == "__main__":
    unittest.main()
