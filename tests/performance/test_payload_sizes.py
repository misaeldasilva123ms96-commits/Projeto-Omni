"""Phase 30.12 — payload size and timeline growth audits."""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.control import GovernanceResolutionController, RunRegistry, RunStatus  # noqa: E402
from brain.runtime.control.governance_read_model import build_operational_governance_snapshot  # noqa: E402
from brain.runtime.control.governance_timeline import build_governance_timeline_event  # noqa: E402
from brain.runtime.language import InputInterpreter  # noqa: E402
from brain.runtime.observability.performance_metrics import json_payload_utf8_bytes  # noqa: E402


class PayloadSizeAuditTest(unittest.TestCase):
    def setUp(self) -> None:
        self._workspace = Path(tempfile.mkdtemp(prefix="payload3012-"))

    def tearDown(self) -> None:
        shutil.rmtree(self._workspace, ignore_errors=True)

    def test_oil_request_payload_stays_bounded(self) -> None:
        interpreter = InputInterpreter()
        req = interpreter.interpret(
            "Explique governança operacional e limites de payload em poucas frases.",
            session_id="pl-s1",
            user_language="pt-BR",
        )
        size = json_payload_utf8_bytes(req.serialize())
        self.assertLess(size, 32_768, msg=f"OILRequest JSON unexpectedly large: {size} bytes")

    def test_governance_timeline_event_payload_stays_bounded(self) -> None:
        ev = build_governance_timeline_event(
            event_type="hold",
            timestamp="2026-04-15T12:00:00+00:00",
            current_resolution="hold",
            previous_resolution="running",
            reason="governance_hold",
            decision_source="runtime_orchestrator",
            run_status="awaiting_approval",
        )
        size = json_payload_utf8_bytes(ev)
        self.assertLess(size, 4096, msg=f"timeline event unexpectedly large: {size} bytes")

    def test_timeline_length_capped_under_many_transitions(self) -> None:
        registry = RunRegistry(self._workspace)
        controller = GovernanceResolutionController(registry)
        controller.register_run_start(
            run_id="grow-run",
            goal_id=None,
            session_id="pl-s2",
            status=RunStatus.RUNNING,
            last_action="execution_started",
            progress_score=0.0,
        )
        for i in range(120):
            controller.transition_run(
                run_id="grow-run",
                status=RunStatus.RUNNING,
                last_action=f"tick_{i}",
                progress=min(0.99, 0.01 * (i + 1)),
                reason=None,
                decision_source="runtime_orchestrator",
            )
        rec = registry.get("grow-run")
        self.assertIsNotNone(rec)
        self.assertLessEqual(len(rec.governance_timeline), 80, msg="timeline cap (80) violated")

    def test_operational_governance_snapshot_stays_bounded_for_many_runs(self) -> None:
        registry = RunRegistry(self._workspace)
        controller = GovernanceResolutionController(registry)
        for n in range(25):
            rid = f"multi-{n}"
            controller.register_run_start(
                run_id=rid,
                goal_id=f"g-{n}",
                session_id="pl-s3",
                status=RunStatus.RUNNING,
                last_action="execution_started",
                progress_score=0.0,
            )
            if n % 4 == 0:
                controller.handle_governance_hold(run_id=rid, progress=0.2)
        snap = build_operational_governance_snapshot(registry, timeline_limit=25)
        size = json_payload_utf8_bytes(snap)
        self.assertLess(size, 512_000, msg=f"snapshot unexpectedly large: {size} bytes")
