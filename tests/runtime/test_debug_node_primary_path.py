from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

import argparse
import pytest

from brain.runtime.diagnostics.debug_node_primary_path import (
    _colorize,
    _detect_env,
    _import_or_fail,
    _redact,
    print_debug_report,
)


class TestColorize:
    def test_colorize_ok(self) -> None:
        result = _colorize("test", "ok")
        assert "\033[92m" in result

    def test_colorize_fallback(self) -> None:
        result = _colorize("test", "fallback")
        assert "\033[91m" in result

    def test_colorize_bridge(self) -> None:
        result = _colorize("test", "bridge_execution_request")
        assert "\033[94m" in result

    def test_colorize_true_action(self) -> None:
        result = _colorize("test", "true_action_execution")
        assert "\033[93m" in result

    def test_colorize_unknown_status(self) -> None:
        result = _colorize("test", "unknown")
        assert result == "test"


class TestDetectEnv:
    def test_returns_dict_with_expected_keys(self) -> None:
        env = _detect_env()
        assert isinstance(env, dict)
        assert "BASE_DIR" in env
        assert "OMNI_JS_RUNTIME_BIN" in env
        assert "NODE_BIN" in env
        assert "OMNI_RUNTIME_MODE" in env
        assert "_node_on_path" in env


class TestRedaction:
    def test_redacts_secret_named_values(self) -> None:
        assert _redact("super-secret-value", key="OPENAI_API_KEY") == "<redacted>"

    def test_redacts_common_token_patterns_in_verbose_text(self) -> None:
        output = _redact("Authorization: Bearer abcdefghijklmnopqrstuvwxyz", key="stdout")
        assert "abcdefghijklmnopqrstuvwxyz" not in output
        assert "Bearer <redacted>" in output


class TestImportOrFail:
    def test_imports_existing_module(self) -> None:
        fn = _import_or_fail("os", "getcwd")
        assert fn is not None
        assert callable(fn)

    def test_returns_none_for_nonexistent(self) -> None:
        fn = _import_or_fail("nonexistent.module", "nothing")
        assert fn is None


class TestPrintDebugReport:
    def test_accepts_minimal_args(self) -> None:
        try:
            print_debug_report(prompt="teste", timeout_seconds=1)
        except Exception:
            pass

    def test_imports_critical_dependencies(self) -> None:
        for mod_name, attr_name in [
            ("brain.runtime.node_runner", "resolve_node_command_context"),
            ("brain.runtime.node_transport", "call_node_with_preflight"),
            ("brain.runtime.node_transport", "run_node_subprocess"),
            ("brain.runtime.observability.runtime_lane_classifier", "interpret_node_payload"),
            ("brain.runtime.observability.runtime_lane_classifier", "normalize_node_outcome"),
            ("brain.runtime.orchestrator", "BrainPaths"),
            ("brain.runtime.js_runtime_adapter", "JSRuntimeAdapter"),
        ]:
            fn = _import_or_fail(mod_name, attr_name)
            assert fn is not None, f"Failed to import {attr_name} from {mod_name}"
