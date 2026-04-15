from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.control import GovernanceResolutionController, RunRegistry, RunStatus  # noqa: E402
from brain.runtime.control.governance_read_model import build_operational_governance_snapshot  # noqa: E402
from brain.runtime.language import InputInterpreter, OILResult, OutputComposer  # noqa: E402
from brain.runtime.observability.run_reader import read_operational_governance  # noqa: E402
from brain.runtime.orchestrator_services import GovernanceIntegrationService, RunLifecycleService  # noqa: E402


def _workspace_root() -> Path:
    root = Path(tempfile.mkdtemp(prefix="phase3011-integration-"))
    return root


def test_input_interpretation_to_oil_and_output_composition_path_is_coherent() -> None:
    interpreter = InputInterpreter()
    composer = OutputComposer()

    request = interpreter.interpret(
        "Resuma o status do RunRegistry em 3 pontos.",
        session_id="sess-int-1",
        user_language="pt-BR",
    )
    payload = request.serialize()

    assert payload["oil_version"] == "1.0"
    assert payload["intent"]
    assert payload["context"]["session_id"] == "sess-int-1"

    result = OILResult.deserialize(
        {
            "oil_version": "1.0",
            "result_type": "summary",
            "status": "success",
            "data": {"summary": "RunRegistry consolidado e operativo."},
        }
    )
    text = composer.compose(result, user_language="pt-BR")
    assert "RunRegistry" in text


def test_governance_controller_registry_timeline_and_operational_snapshot_stay_coherent() -> None:
    root = _workspace_root()
    try:
        registry = RunRegistry(root)
        controller = GovernanceResolutionController(registry)
        run_id = "run-int-governance"

        controller.register_run_start(
            run_id=run_id,
            goal_id="goal-int",
            session_id="sess-int",
            status=RunStatus.RUNNING,
            last_action="execution_started",
            progress_score=0.0,
            metadata={"operator_control_enabled": True},
        )
        controller.handle_governance_hold(run_id=run_id, progress=0.2)
        controller.handle_operator_action(run_id=run_id, action="approve", progress=0.5)
        controller.handle_completion(run_id=run_id, progress=1.0)

        rec = registry.get(run_id)
        assert rec is not None
        event_types = [row.get("event_type") for row in rec.governance_timeline]
        assert "start" in event_types
        assert "hold" in event_types
        assert "approve" in event_types
        assert "complete" in event_types

        snapshot = build_operational_governance_snapshot(registry)
        assert "summary" in snapshot
        assert "latest_governance_event_by_run" in snapshot
        assert run_id in snapshot["latest_governance_event_by_run"]

        read_back = read_operational_governance(root)
        assert read_back["total_runs"] >= 1
        assert run_id in read_back["latest_governance_event_by_run"]
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_governance_integration_timeout_path_updates_registry_via_run_lifecycle() -> None:
    root = _workspace_root()
    try:
        registry = RunRegistry(root)
        run_id = "run-int-timeout"

        run_lifecycle = RunLifecycleService(run_registry=registry, get_controller=lambda: None)
        run_lifecycle.register_run_start(
            run_id=run_id,
            session_id="sess-int-timeout",
            goal_id=None,
            status=RunStatus.PAUSED,
            last_action="operator_pause",
            progress_score=0.25,
            metadata={"operator_control_enabled": True},
        )

        service = GovernanceIntegrationService(
            run_registry=registry,
            get_controller=lambda: None,
            run_lifecycle=run_lifecycle,
        )
        previous_poll = os.environ.get("OMINI_RUN_CONTROL_POLL_SECONDS")
        previous_wait = os.environ.get("OMINI_RUN_CONTROL_MAX_WAIT_SECONDS")
        os.environ["OMINI_RUN_CONTROL_POLL_SECONDS"] = "0.05"
        os.environ["OMINI_RUN_CONTROL_MAX_WAIT_SECONDS"] = "0.1"
        try:
            clearance = service.await_run_control_clearance(run_id=run_id)
        finally:
            if previous_poll is None:
                os.environ.pop("OMINI_RUN_CONTROL_POLL_SECONDS", None)
            else:
                os.environ["OMINI_RUN_CONTROL_POLL_SECONDS"] = previous_poll
            if previous_wait is None:
                os.environ.pop("OMINI_RUN_CONTROL_MAX_WAIT_SECONDS", None)
            else:
                os.environ["OMINI_RUN_CONTROL_MAX_WAIT_SECONDS"] = previous_wait

        assert clearance["status"] == "failed"
        assert clearance["error"] == "operator_timeout"
        record = registry.get(run_id)
        assert record is not None
        assert record.status == RunStatus.FAILED
        assert record.last_action == "operator_timeout"
    finally:
        shutil.rmtree(root, ignore_errors=True)
