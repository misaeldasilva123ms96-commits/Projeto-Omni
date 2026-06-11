from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.sandbox.policy_engine import classify_command  # noqa: E402
from brain.runtime.sandbox.policy_types import PolicyInput  # noqa: E402
from brain.runtime.sandbox.runtime_truth import (  # noqa: E402
    SANDBOX_POLICY_RUNTIME_MODE,
    build_sandbox_policy_evidence,
)


def _evidence_for(command: str):
    policy_input = PolicyInput(
        command=command,
        cwd=".",
        requested_by="test",
        sandbox_mode="local",
    )
    decision = classify_command(
        policy_input.command,
        cwd=policy_input.cwd,
        requested_by=policy_input.requested_by,
        sandbox_mode=policy_input.sandbox_mode,
    )
    return build_sandbox_policy_evidence(
        policy_input,
        decision,
        timestamp="2026-06-10T00:00:00+00:00",
    )


def test_allowed_command_evidence() -> None:
    evidence = _evidence_for("git status")
    payload = evidence.to_dict()

    assert payload["event_type"] == "sandbox.policy_decision"
    assert payload["command"] == "git status"
    assert payload["normalized_command"] == "git status"
    assert payload["governance_decision"] == "allowed"
    assert payload["policy_allowed"] is True
    assert payload["execution_attempted"] is False
    assert payload["command_executed"] is False


def test_approval_required_command_evidence() -> None:
    evidence = _evidence_for("npm test")
    payload = evidence.to_dict()

    assert payload["governance_decision"] == "requires_approval"
    assert payload["policy_requires_approval"] is True
    assert payload["execution_attempted"] is False
    assert payload["command_executed"] is False


def test_blocked_command_evidence() -> None:
    evidence = _evidence_for("cat .env")
    payload = evidence.to_dict()

    assert payload["governance_decision"] == "blocked"
    assert payload["policy_blocked"] is True
    assert payload["execution_attempted"] is False
    assert payload["command_executed"] is False


def test_unknown_command_evidence() -> None:
    evidence = _evidence_for("bash script.sh")
    payload = evidence.to_dict()

    assert payload["governance_decision"] == "blocked"
    assert payload["policy_category"] == "unknown"
    assert payload["execution_attempted"] is False
    assert payload["command_executed"] is False


def test_evidence_is_json_serializable() -> None:
    payload = _evidence_for("git status").to_dict()
    encoded = json.dumps(payload, sort_keys=True)

    assert "sandbox.policy_decision" in encoded
    assert "2026-06-10T00:00:00+00:00" in encoded


def test_safety_defaults() -> None:
    payload = _evidence_for("git status").to_dict()

    assert payload["runtime_mode"] == SANDBOX_POLICY_RUNTIME_MODE
    assert payload["execution_attempted"] is False
    assert payload["command_executed"] is False
    assert payload["network_used"] is False
    assert payload["secrets_detected"] is False
    assert payload["evidence_version"] == "1.0"
