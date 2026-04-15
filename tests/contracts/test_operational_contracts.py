from __future__ import annotations

import io
import json
import shutil
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.control import (  # noqa: E402
    GovernanceResolutionController,
    RunRegistry,
    RunStatus,
    assert_operational_governance_contract,
)
from brain.runtime.control.cli import main as control_cli_main  # noqa: E402
from brain.runtime.control.governance_read_model import build_operational_governance_snapshot  # noqa: E402
from brain.runtime.control.governance_timeline import GovernanceTimelineEventType, build_governance_timeline_event  # noqa: E402
from brain.runtime.language import OILError, OILRequest, OILResult  # noqa: E402


def _workspace_root() -> Path:
    return Path(tempfile.mkdtemp(prefix="phase3011-contracts-"))


def test_oil_request_result_error_contract_serialization_is_stable() -> None:
    req = OILRequest.deserialize({"oil_version": "1.0", "intent": "ask_question"})
    req_wire = req.serialize()
    assert req_wire["oil_version"] == "1.0"
    assert req_wire["intent"] == "ask_question"

    result = OILResult.deserialize(
        {
            "oil_version": "1.0",
            "result_type": "summary",
            "status": "success",
            "data": {"summary": "ok"},
        }
    )
    result_wire = result.serialize()
    assert result_wire["result_type"] == "summary"
    assert isinstance(result_wire["data"], dict)

    err = OILError.deserialize(
        {
            "oil_version": "1.0",
            "error": {"code": "AMBIGUOUS_INTENT", "message": "need clarification", "recoverable": True},
        }
    )
    err_wire = err.serialize()
    assert err_wire["status"] == "error"
    assert err_wire["error"]["recoverable"] is True


def test_governance_timeline_event_contract_shape_is_stable() -> None:
    event = build_governance_timeline_event(
        event_type=GovernanceTimelineEventType.HOLD.value,
        timestamp="2026-04-15T00:00:00+00:00",
        current_resolution="hold",
        previous_resolution="running",
        reason="governance_hold",
        decision_source="runtime_orchestrator",
        run_status="awaiting_approval",
    )
    assert set(event.keys()) >= {
        "event_type",
        "timestamp",
        "resolution",
        "previous_resolution",
        "run_status",
        "governance",
    }
    assert set(event["governance"].keys()) >= {"reason", "severity", "source"}


def test_operational_governance_snapshot_contract_shape_is_stable() -> None:
    root = _workspace_root()
    try:
        registry = RunRegistry(root)
        controller = GovernanceResolutionController(registry)
        controller.register_run_start(
            run_id="run-contract-1",
            goal_id=None,
            session_id="sess-contract-1",
            status=RunStatus.RUNNING,
            last_action="execution_started",
            progress_score=0.0,
            metadata={"operator_control_enabled": True},
        )
        controller.handle_governance_hold(run_id="run-contract-1", progress=0.2)
        snapshot = build_operational_governance_snapshot(registry, timeline_limit=10)
        assert_operational_governance_contract(snapshot)
        assert set(snapshot.keys()) >= {
            "summary",
            "total_runs",
            "waiting_operator_runs",
            "operator_attention_runs",
            "latest_governance_event_by_run",
            "recent_governance_timeline_events",
        }
        assert "run-contract-1" in snapshot["latest_governance_event_by_run"]
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_governance_cli_output_remains_json_compatible() -> None:
    root = _workspace_root()
    try:
        registry = RunRegistry(root)
        controller = GovernanceResolutionController(registry)
        controller.register_run_start(
            run_id="run-cli-contract",
            goal_id=None,
            session_id="sess-cli-contract",
            status=RunStatus.RUNNING,
            last_action="execution_started",
            progress_score=0.0,
            metadata={"operator_control_enabled": True},
        )
        controller.handle_governance_hold(run_id="run-cli-contract", progress=0.3)

        for argv in (
            ["control-cli", "--root", str(root), "inspect_run", "run-cli-contract"],
            ["control-cli", "--root", str(root), "governance_snapshot"],
        ):
            stream = io.StringIO()
            with patch.object(sys, "argv", argv):
                with redirect_stdout(stream):
                    exit_code = control_cli_main()
            assert exit_code == 0
            payload = json.loads(stream.getvalue())
            assert payload["status"] == "ok"
            if argv[3] == "inspect_run":
                run_payload = payload["run"]
                assert isinstance(run_payload.get("governance_timeline"), list)
                assert isinstance(run_payload.get("resolution"), dict)
            else:
                governance = payload["governance"]
                assert isinstance(governance.get("summary"), dict)
                assert isinstance(governance.get("operator_attention_runs"), list)
    finally:
        shutil.rmtree(root, ignore_errors=True)
