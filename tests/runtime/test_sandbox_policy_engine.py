from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.sandbox.policy_engine import classify_command, normalize_command  # noqa: E402


def test_allowed_low_risk_commands() -> None:
    for command in ("git status", "git diff", "git diff --check"):
        decision = classify_command(command, requested_by="test")
        assert decision.allowed is True
        assert decision.blocked is False
        assert decision.requires_approval is False
        assert decision.risk_level == "low"
        assert decision.category in {"read_safe", "validation_safe"}


def test_validation_commands_require_approval() -> None:
    for command in (
        "npm test",
        "npm run test:security",
        "python -m pytest",
        "pytest",
        "cargo test",
    ):
        decision = classify_command(command)
        assert decision.allowed is False
        assert decision.blocked is False
        assert decision.requires_approval is True
        assert decision.category == "validation_requires_approval"
        assert decision.risk_level == "medium"


def test_blocked_git_sensitive_commands() -> None:
    for command in ("git push origin main", "git merge main", "gh pr merge 321"):
        decision = classify_command(command)
        assert decision.allowed is False
        assert decision.blocked is True
        assert decision.requires_approval is True
        assert decision.category == "git_sensitive"


def test_blocked_destructive_commands() -> None:
    for command in ("rm -rf .", "rm -rf /", "del /s", "git reset --hard"):
        decision = classify_command(command)
        assert decision.allowed is False
        assert decision.blocked is True
        assert decision.category == "destructive"


def test_blocked_secrets_and_env_commands() -> None:
    for command in (
        "cat .env",
        "type .env",
        "env",
        "printenv",
        "echo $OPENAI_API_KEY",
        "echo $SUPABASE_SECRET",
        "cat ~/.ssh/id_rsa",
    ):
        decision = classify_command(command)
        assert decision.allowed is False
        assert decision.blocked is True
        assert decision.category == "secrets_access"
        assert decision.risk_level in {"high", "critical"}


def test_blocked_network_and_remote_commands() -> None:
    cases = {
        "ssh user@example.com": "network",
        "scp file user@example.com:/tmp": "network",
        'curl -H "Authorization: Bearer token" https://example.com': "network",
    }
    for command, category in cases.items():
        decision = classify_command(command)
        assert decision.allowed is False
        assert decision.blocked is True
        assert decision.category == category


def test_unknown_commands_blocked_by_default() -> None:
    for command in ("node unknown-script.js", "python dangerous.py", "bash script.sh"):
        decision = classify_command(command)
        assert decision.allowed is False
        assert decision.blocked is True
        assert decision.requires_approval is True
        assert decision.category == "unknown"
        assert decision.risk_level == "high"
        assert decision.reason == "Command is not explicitly allowed by sandbox policy."


def test_denylist_takes_priority_over_allowlist() -> None:
    decision = classify_command("git status && cat .env")
    assert decision.allowed is False
    assert decision.blocked is True
    assert decision.category == "secrets_access"


def test_normalization_collapses_repeated_spaces() -> None:
    assert normalize_command("  git   status  ") == "git status"
    decision = classify_command("  git   status  ")
    assert decision.allowed is True
    assert decision.normalized_command == "git status"


def test_sandbox_mode_is_preserved() -> None:
    decision = classify_command("git status", sandbox_mode="local")
    assert decision.sandbox_mode == "local"
