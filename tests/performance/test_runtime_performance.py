"""Phase 30.12 — coarse timing visibility for critical paths (measurement only)."""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.control import GovernanceResolutionController, RunRegistry, RunStatus  # noqa: E402
from brain.runtime.language import InputInterpreter, OILResult, OutputComposer  # noqa: E402
from brain.runtime.observability.performance_metrics import measure_call_ms  # noqa: E402
from brain.runtime.orchestrator import BrainOrchestrator, BrainPaths  # noqa: E402
from brain.runtime.orchestration import OrchestrationExecutor  # noqa: E402
from brain.runtime.planning.planning_executor import PlanningExecutor  # noqa: E402


# Loose ceilings: visibility and regression guardrails, not micro-benchmarks (CI-safe).
_MAX_SEGMENT_MS = 45_000.0
_MAX_TOTAL_MS = 120_000.0


class RuntimePerformanceAuditTest(unittest.TestCase):
    def setUp(self) -> None:
        # Isolated workspace for planning/registry-backed steps (BrainPaths still resolves the repo root).
        self._workspace = Path(tempfile.mkdtemp(prefix="perf3012-"))

    def tearDown(self) -> None:
        shutil.rmtree(self._workspace, ignore_errors=True)

    def test_step_level_timing_breakdown_is_bounded(self) -> None:
        timings: dict[str, float] = {}

        def time_key(key: str, fn):
            _, ms = measure_call_ms(fn)
            timings[key] = ms

        interpreter = InputInterpreter()

        time_key(
            "interpret",
            lambda: interpreter.interpret(
                "Resuma o papel do RunRegistry e da linha do tempo de governança.",
                session_id="perf-sess",
                user_language="pt-BR",
            ),
        )

        registry = RunRegistry(self._workspace)
        controller = GovernanceResolutionController(registry)

        def governance_path():
            controller.register_run_start(
                run_id="perf-run",
                goal_id="perf-goal",
                session_id="perf-sess",
                status=RunStatus.RUNNING,
                last_action="execution_started",
                progress_score=0.0,
                metadata={"operator_control_enabled": True},
            )
            for i in range(12):
                controller.transition_run(
                    run_id="perf-run",
                    status=RunStatus.RUNNING,
                    last_action=f"heartbeat_{i}",
                    progress=min(0.95, 0.05 * (i + 1)),
                    reason=None,
                    decision_source="runtime_orchestrator",
                )
            controller.handle_governance_hold(run_id="perf-run", progress=0.5)
            controller.handle_operator_action(run_id="perf-run", action="approve", progress=0.9)
            controller.handle_completion(run_id="perf-run", progress=1.0)

        time_key("governance", governance_path)

        composer = OutputComposer()
        sample = OILResult(
            oil_version="1.0",
            result_type="summary",
            status="success",
            data={"summary": "Governança e registro de execução permanecem coerentes."},
        )
        time_key("compose_output", lambda: composer.compose(sample, user_language="pt-BR"))

        planning = PlanningExecutor(self._workspace)
        _, plan = planning.ensure_plan(
            session_id="perf-sess-plan",
            task_id="perf-task-plan",
            run_id="perf-run-plan",
            message="workflow cognitivo",
            actions=[
                {"step_id": "read", "selected_tool": "filesystem_read"},
                {"step_id": "write", "selected_tool": "filesystem_write"},
            ],
            plan_kind="linear",
        )
        self.assertIsNotNone(plan)
        executor = OrchestrationExecutor(self._workspace)

        def orchestrate_once():
            return executor.orchestrate(
                session_id="perf-sess-plan",
                task_id="perf-task-plan",
                run_id="perf-run-plan",
                action={"step_id": "read", "selected_tool": "filesystem_read", "action_type": "read"},
                plan=plan,
                step_results=[],
                learning_signals=[],
                engineering_tool=False,
            )

        time_key("orchestration", orchestrate_once)

        orch = BrainOrchestrator(BrainPaths.from_entrypoint(PROJECT_ROOT / "backend" / "python" / "main.py"))

        def orchestrator_lifecycle():
            orch._register_run_record(
                run_id="perf-orch",
                session_id="perf-sess",
                goal_id=None,
                status=RunStatus.RUNNING,
                last_action="execution_started",
                progress_score=0.0,
                metadata={"operator_control_enabled": True},
            )
            orch._update_run_status(
                run_id="perf-orch",
                status=RunStatus.RUNNING,
                last_action="heartbeat",
                progress_score=0.2,
            )

        time_key("orchestrator_lifecycle", orchestrator_lifecycle)

        total_ms = sum(timings.values())
        for name, ms in timings.items():
            self.assertGreaterEqual(ms, 0.0, msg=f"{name} timing invalid")
            self.assertLess(ms, _MAX_SEGMENT_MS, msg=f"{name} exceeded soft ceiling ({ms:.1f} ms)")
        self.assertLess(total_ms, _MAX_TOTAL_MS, msg=f"aggregate timing {total_ms:.1f} ms")
