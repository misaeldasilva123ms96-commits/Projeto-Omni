from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.config import load_config  # noqa: E402


def test_node_runtime_config_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "OMNI_NODE_SUBPROCESS_TIMEOUT_SECONDS",
        "OMNI_NODE_CIRCUIT_BREAKER_ENABLED",
        "OMNI_NODE_CIRCUIT_FAILURE_THRESHOLD",
        "OMNI_NODE_CIRCUIT_RESET_SECONDS",
    ):
        monkeypatch.delenv(key, raising=False)
        monkeypatch.delenv(key.replace("OMNI_", "OMINI_"), raising=False)

    config = load_config()

    assert config.node_subprocess_timeout_seconds == 60
    assert config.node_circuit_breaker_enabled is True
    assert config.node_circuit_failure_threshold == 3
    assert config.node_circuit_reset_seconds == 30


def test_node_runtime_config_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OMNI_NODE_SUBPROCESS_TIMEOUT_SECONDS", "9999")
    monkeypatch.setenv("OMNI_NODE_CIRCUIT_FAILURE_THRESHOLD", "0")
    monkeypatch.setenv("OMNI_NODE_CIRCUIT_RESET_SECONDS", "99999")

    config = load_config()

    assert config.node_subprocess_timeout_seconds == 300
    assert config.node_circuit_failure_threshold == 1
    assert config.node_circuit_reset_seconds == 3600
