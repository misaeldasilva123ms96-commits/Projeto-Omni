from __future__ import annotations

import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.learning.learning_logger import LearningLogger  # noqa: E402
from brain.runtime.learning.learning_safety import (  # noqa: E402
    build_learning_safety_metadata,
    classify_learning_record,
    should_save_positive_learning,
)


def _record(**overrides):
    payload = {
        "runtime_mode": "FULL_COGNITIVE_RUNTIME",
        "success": True,
        "failure_class": "",
        "decision_evaluation": {"decision_issue": ""},
        "execution_outcome": {
            "runtime_mode": "FULL_COGNITIVE_RUNTIME",
            "fallback_triggered": False,
            "provider_failed": False,
            "tool_used": "",
            "tool_succeeded": None,
            "tool_failed": None,
            "tool_denied": None,
        },
        "metadata": {
            "runtime_truth_confidence": "high",
            "provider_succeeded": True,
            "decision_requires_tools": False,
        },
    }
    payload.update(overrides)
    return payload


def test_fallback_and_unsafe_runtime_modes_are_not_positive() -> None:
    cases = [
        ("SAFE_FALLBACK", "failure_memory"),
        ("NODE_FALLBACK", "failure_memory"),
        ("PROVIDER_UNAVAILABLE", "failure_memory"),
        ("TOOL_BLOCKED", "governance_block_case"),
        ("MATCHER_SHORTCUT", "routing_eval_case"),
    ]

    for runtime_mode, expected_classification in cases:
        payload = _record(
            runtime_mode=runtime_mode,
            execution_outcome={
                "runtime_mode": runtime_mode,
                "fallback_triggered": runtime_mode == "SAFE_FALLBACK",
                "provider_failed": runtime_mode == "PROVIDER_UNAVAILABLE",
            },
        )
        assert classify_learning_record(payload) == expected_classification
        assert should_save_positive_learning(payload) is False


def test_provider_tool_and_governance_failures_are_not_positive() -> None:
    provider_failed = _record(
        execution_outcome={"runtime_mode": "FULL_COGNITIVE_RUNTIME", "fallback_triggered": False, "provider_failed": True},
        metadata={"runtime_truth_confidence": "high", "provider_succeeded": False},
    )
    tool_blocked = _record(
        execution_outcome={"runtime_mode": "TOOL_BLOCKED", "fallback_triggered": False, "tool_used": "write_file", "tool_denied": True},
        metadata={"runtime_truth_confidence": "high", "provider_succeeded": True, "tool_status": "blocked"},
    )
    governance_blocked = _record(
        metadata={"runtime_truth_confidence": "high", "provider_succeeded": True, "governance_status": "blocked"},
    )

    assert build_learning_safety_metadata(provider_failed)["learning_safety_reason"] == "provider_not_successful"
    assert build_learning_safety_metadata(tool_blocked)["tool_status"] == "blocked"
    assert build_learning_safety_metadata(governance_blocked)["governance_status"] == "blocked"
    assert should_save_positive_learning(provider_failed) is False
    assert should_save_positive_learning(tool_blocked) is False
    assert should_save_positive_learning(governance_blocked) is False


def test_public_error_severity_becomes_failure_or_diagnostic_not_positive() -> None:
    payload = _record(
        metadata={
            "runtime_truth_confidence": "high",
            "provider_succeeded": True,
            "error_public_code": "NODE_RUNNER_FAILED",
        }
    )

    safety = build_learning_safety_metadata(payload)

    assert safety["learning_classification"] == "failure_memory"
    assert safety["positive_training_candidate"] is False
    assert safety["negative_training_candidate"] is True


def test_clean_full_runtime_success_can_be_positive() -> None:
    payload = _record()

    safety = build_learning_safety_metadata(payload)

    assert safety["learning_classification"] == "positive_training_candidate"
    assert safety["positive_training_candidate"] is True
    assert safety["negative_training_candidate"] is False


def test_redaction_and_safety_metadata_are_persisted_by_learning_logger() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        logger = LearningLogger(Path(tmp))
        result = logger.log_turn(
            input_text="user@example.com pediu segredo sk-proj-abcdefghijklmnop",
            response_text="ok sem segredo",
            strategy_execution={"selected_strategy": "DIRECT_RESPONSE"},
            decision_ranking={},
            cognitive_runtime_inspection={
                "runtime_mode": "FULL_COGNITIVE_RUNTIME",
                "signals": {
                    "execution_path_used": "node_execution",
                    "fallback_triggered": False,
                    "provider_failed": False,
                    "provider_succeeded": True,
                    "runtime_truth_confidence": "high",
                },
            },
            tool_execution=None,
        )

        record = result["record"]
        raw_text = logger.store.records_path.read_text(encoding="utf-8")

        assert "user@example.com" not in raw_text
        assert "sk-proj-" not in raw_text
        assert record["learning_safety"]["positive_training_candidate"] is True
        assert record["learning_safety"]["learning_classification"] == "positive_training_candidate"
        assert "learning_safety_reason" in record["learning_safety"]


def test_backward_compatible_records_do_not_crash_classifier() -> None:
    safety = build_learning_safety_metadata({"runtime_mode": "UNKNOWN_LEGACY"})

    assert safety["learning_classification"] == "diagnostic_memory"
    assert safety["positive_training_candidate"] is False
    assert safety["runtime_mode"] == "UNKNOWN_LEGACY"
