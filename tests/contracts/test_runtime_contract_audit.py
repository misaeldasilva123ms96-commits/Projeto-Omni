"""Phase 30.12 — cross-layer contract stability audit (extends 30.11 contracts)."""

from __future__ import annotations

import io
import json
import shutil
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.control import (  # noqa: E402
    GovernanceResolutionController,
    RunRegistry,
    RunStatus,
    assert_operational_governance_contract,
    validate_operational_governance_shape,
)
from brain.runtime.control.cli import main as control_cli_main  # noqa: E402
from brain.runtime.control.governance_read_model import build_operational_governance_snapshot  # noqa: E402
from brain.runtime.language import OILRequest, OILResult, OutputComposer  # noqa: E402
from brain.runtime.observability.run_reader import read_operational_governance  # noqa: E402


@pytest.fixture()
def workspace_root():
    root = Path(tempfile.mkdtemp(prefix="contract3012-"))
    yield root
    shutil.rmtree(root, ignore_errors=True)


def test_oil_result_round_trip_and_output_compose_contract(workspace_root: Path) -> None:
    req = OILRequest.deserialize({"oil_version": "1.0", "intent": "summarize"})
    wire = json.dumps(req.serialize())
    back = OILRequest.deserialize(json.loads(wire))
    assert back.intent == "summarize"

    res = OILResult.deserialize(
        {
            "oil_version": "1.0",
            "result_type": "answer",
            "status": "success",
            "data": {"answer": "Resposta estruturada."},
        }
    )
    text = OutputComposer().compose(res, user_language="pt-BR")
    assert len(text) > 0


def test_governance_snapshot_and_read_model_align(workspace_root: Path) -> None:
    registry = RunRegistry(workspace_root)
    ctrl = GovernanceResolutionController(registry)
    ctrl.register_run_start(
        run_id="audit-1",
        goal_id="g-audit",
        session_id="s-audit",
        status=RunStatus.RUNNING,
        last_action="execution_started",
        progress_score=0.0,
    )
    ctrl.handle_governance_hold(run_id="audit-1", progress=0.3)
    snap = build_operational_governance_snapshot(registry, timeline_limit=15)
    assert_operational_governance_contract(snap)
    assert not validate_operational_governance_shape(snap)

    read_back = read_operational_governance(workspace_root, timeline_limit=15)
    assert read_back["total_runs"] == snap["total_runs"]
    assert set(read_back.keys()) >= {"summary", "latest_governance_event_by_run"}


def test_control_cli_governance_json_contract(workspace_root: Path) -> None:
    registry = RunRegistry(workspace_root)
    ctrl = GovernanceResolutionController(registry)
    ctrl.register_run_start(
        run_id="cli-audit",
        goal_id=None,
        session_id="s-cli",
        status=RunStatus.AWAITING_APPROVAL,
        last_action="governance_hold",
        progress_score=0.4,
    )
    for argv in (
        ["control-cli", "--root", str(workspace_root), "list_runs", "--limit", "5"],
        ["control-cli", "--root", str(workspace_root), "resolution_summary"],
        ["control-cli", "--root", str(workspace_root), "governance_operational"],
    ):
        stream = io.StringIO()
        with patch.object(sys, "argv", argv):
            with redirect_stdout(stream):
                code = control_cli_main()
        assert code == 0
        payload = json.loads(stream.getvalue())
        assert payload.get("status") == "ok"
        if argv[3] == "list_runs":
            assert isinstance(payload.get("runs"), list)
        if argv[3] == "resolution_summary":
            summary = payload.get("summary")
            assert isinstance(summary, dict)
            assert "total_runs" in summary
        if argv[3] == "governance_operational":
            gov = payload.get("governance")
            assert isinstance(gov, dict)
            assert "summary" in gov
