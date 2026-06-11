from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.sandbox.policy_engine import classify_command  # noqa: E402
from brain.runtime.sandbox.policy_types import PolicyInput  # noqa: E402
from brain.runtime.sandbox.reports import (  # noqa: E402
    redact_report_text,
    render_sandbox_policy_report,
)
from brain.runtime.sandbox.runtime_truth import build_sandbox_policy_evidence  # noqa: E402


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


def test_allowed_command_report() -> None:
    report = render_sandbox_policy_report(_evidence_for("git status"))

    assert report.governance_decision == "allowed"
    assert report.execution_attempted is False
    assert report.command_executed is False
    assert "SANDBOX_POLICY_ONLY" in report.markdown
    assert "execution_attempted: false" in report.markdown
    assert "command_executed: false" in report.markdown


def test_approval_required_command_report() -> None:
    report = render_sandbox_policy_report(_evidence_for("npm test"))

    assert report.governance_decision == "requires_approval"
    assert "requires_approval" in report.markdown


def test_blocked_command_report_redacts_env_access() -> None:
    report = render_sandbox_policy_report(_evidence_for("cat .env"))

    assert report.governance_decision == "blocked"
    assert "cat .env" not in report.markdown
    assert "[REDACTED]" in report.markdown


def test_unknown_command_report() -> None:
    report = render_sandbox_policy_report(_evidence_for("bash script.sh"))

    assert report.governance_decision == "blocked"
    assert "unknown" in report.markdown


def test_secret_redaction() -> None:
    redacted_key = redact_report_text("echo $OPENAI_API_KEY")
    redacted_bearer = redact_report_text('curl -H "Authorization: Bearer token"')

    assert "OPENAI_API_KEY" not in redacted_key
    assert "Authorization: Bearer token" not in redacted_bearer
    assert "[REDACTED]" in redacted_key
    assert "[REDACTED]" in redacted_bearer


def test_report_is_dict_convertible() -> None:
    report = render_sandbox_policy_report(_evidence_for("git status"))
    payload = report.to_dict()

    assert payload["suggested_filename"] == "2026-06-10-sandbox-policy-decision.md"
    assert payload["suggested_vault_path"] == (
        "vault/09_Sandbox_Reports/2026-06-10-sandbox-policy-decision.md"
    )
    assert payload["evidence_event_type"] == "sandbox.policy_decision"


def test_renderer_returns_only_markdown_and_suggested_path() -> None:
    report = render_sandbox_policy_report(_evidence_for("git status"))

    assert isinstance(report.markdown, str)
    assert isinstance(report.suggested_vault_path, str)
    assert report.suggested_vault_path.endswith(".md")
    assert report.suggested_vault_path == (
        "vault/09_Sandbox_Reports/2026-06-10-sandbox-policy-decision.md"
    )
