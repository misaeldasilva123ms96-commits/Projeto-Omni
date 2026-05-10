from __future__ import annotations

import copy
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.observability.cognitive_runtime_inspector import build_cognitive_runtime_inspection  # noqa: E402
from brain.runtime.observability.public_runtime_payload import build_public_cognitive_runtime_inspection  # noqa: E402
from brain.runtime.observability.runtime_lane_classifier import (  # noqa: E402
    LANE_LOCAL_DIRECT_RESPONSE,
    LANE_MATCHER_SHORTCUT,
    LANE_SAFE_DEGRADED_FALLBACK,
    LANE_TRUE_ACTION_EXECUTION,
    TRANSPORT_FALLBACK,
    TRANSPORT_SUCCESS,
    normalize_node_outcome,
)


def _contains_key(value, key_name: str) -> bool:
    if isinstance(value, dict):
        return any(str(key) == key_name or _contains_key(item, key_name) for key, item in value.items())
    if isinstance(value, list):
        return any(_contains_key(item, key_name) for item in value)
    return False


def _base_kwargs(**overrides):
    base = dict(
        response="ok",
        safe_fallback="SAFE",
        node_fallback="NODE_FB",
        mock_response="MOCK",
        last_runtime_mode="live",
        last_runtime_reason="node_execution_request",
        reasoning_payload={"trace": {"validation_result": "valid"}},
        strategy_payload={"degraded": False},
        memory_context_payload={"selected_count": 1, "sources_used": ["t"]},
        planning_payload={"planning_trace": {"execution_ready": True, "degraded": False}},
        swarm_result={"response": "ok"},
        learning_record={"assessment": {"execution_path": "swarm"}},
        node_cognitive_hint=None,
        node_outcome=None,
        direct_memory_hit=False,
        self_improving_system_trace={"disabled": False, "idle": True},
        controlled_evolution_payload={"proposal_count": 0},
        coordination_payload={},
        lora_payload=None,
        duration_ms=100,
    )
    base.update(overrides)
    return base


def test_matcher_truth_contract() -> None:
    row = build_cognitive_runtime_inspection(
        **_base_kwargs(
            response="Olá!",
            node_cognitive_hint={"lane": "matcher_shortcut"},
            node_outcome={
                "semantic_lane": LANE_MATCHER_SHORTCUT,
                "transport_status": TRANSPORT_SUCCESS,
                "runtime_truth": {"intent": "greeting", "intent_source": "rule_based", "classifier_version": "regex_v1"},
            },
        )
    )

    truth = row["runtime_truth"]
    assert truth["runtime_mode"] == "MATCHER_SHORTCUT"
    assert truth["error_public_code"] == "MATCHER_SHORTCUT_USED"
    assert truth["matcher_used"] is True
    assert truth["llm_provider_attempted"] is False
    assert truth["tool_invoked"] is False
    assert truth["intent_source"] == "rule_based"
    assert truth["classifier_version"] == "regex_v1"


def test_provider_unavailable_truth_contract() -> None:
    row = build_cognitive_runtime_inspection(
        **_base_kwargs(
            response="provider unavailable",
            swarm_result={
                "metadata": {
                    "execution_provenance": {
                        "provider_actual": "openai",
                        "provider_failed": True,
                        "failure_class": "provider_unavailable",
                    }
                }
            },
        )
    )

    truth = row["runtime_truth"]
    assert truth["runtime_mode"] == "PROVIDER_UNAVAILABLE"
    assert truth["error_public_code"] == "PROVIDER_UNAVAILABLE"
    assert truth["llm_provider_succeeded"] is False


def test_provider_truth_uses_explicit_diagnostics_not_provider_name() -> None:
    row = build_cognitive_runtime_inspection(
        **_base_kwargs(
            response="local plan",
            last_runtime_reason="direct_node_response",
            swarm_result={
                "metadata": {
                    "execution_provenance": {
                        "provider_actual": "openai",
                        "provider_failed": False,
                        "provider_diagnostics": [
                            {
                                "provider": "openai",
                                "selected": True,
                                "attempted": False,
                                "succeeded": False,
                                "failed": False,
                            }
                        ],
                    }
                }
            },
            node_outcome={
                "semantic_lane": LANE_LOCAL_DIRECT_RESPONSE,
                "transport_status": TRANSPORT_SUCCESS,
                "reason_code": "direct_node_response",
            },
        )
    )

    truth = row["runtime_truth"]
    assert truth["runtime_mode"] == "RULE_BASED_INTENT"
    assert truth["llm_provider_attempted"] is False
    assert truth["llm_provider_succeeded"] is False


def test_provider_success_requires_explicit_success_metadata() -> None:
    row = build_cognitive_runtime_inspection(
        **_base_kwargs(
            swarm_result={
                "metadata": {
                    "execution_provenance": {
                        "provider_actual": "openai",
                        "provider_diagnostics": [
                            {
                                "provider": "openai",
                                "selected": True,
                                "attempted": True,
                                "succeeded": True,
                                "failed": False,
                            }
                        ],
                    }
                }
            },
        )
    )

    truth = row["runtime_truth"]
    assert truth["llm_provider_attempted"] is True
    assert truth["llm_provider_succeeded"] is True


def test_tool_blocked_and_tool_executed_truth_contract() -> None:
    blocked = build_cognitive_runtime_inspection(
        **_base_kwargs(
            lora_payload={
                "tool_execution": {
                    "tool_requested": True,
                    "tool_selected": "write_file",
                    "tool_attempted": True,
                    "tool_denied": True,
                    "tool_succeeded": False,
                }
            }
        )
    )
    assert blocked["runtime_truth"]["runtime_mode"] == "TOOL_BLOCKED"
    assert blocked["runtime_truth"]["error_public_code"] == "TOOL_BLOCKED_BY_GOVERNANCE"
    assert blocked["runtime_truth"]["tool_executed"] is False

    executed = build_cognitive_runtime_inspection(
        **_base_kwargs(
            node_outcome={"semantic_lane": LANE_TRUE_ACTION_EXECUTION, "transport_status": TRANSPORT_SUCCESS},
            lora_payload={
                "execution_path_used": "node_execution",
                "tool_execution": {
                    "tool_requested": True,
                    "tool_selected": "read_file",
                    "tool_attempted": True,
                    "tool_succeeded": True,
                },
            },
        )
    )
    assert executed["runtime_truth"]["runtime_mode"] == "TOOL_EXECUTED"
    assert executed["runtime_truth"]["tool_executed"] is True


def test_selected_tool_without_attempt_is_not_invoked() -> None:
    row = build_cognitive_runtime_inspection(
        **_base_kwargs(
            lora_payload={
                "tool_execution": {
                    "tool_requested": True,
                    "tool_selected": "code_search",
                    "tool_attempted": False,
                    "tool_succeeded": False,
                    "tool_denied": False,
                }
            }
        )
    )

    truth = row["runtime_truth"]
    assert truth["tool_invoked"] is False
    assert truth["tool_executed"] is False
    assert truth["tool_status"] == "not_invoked"
    assert row["signals"]["tool_requested"] is True
    assert row["signals"]["tool_selected"] == "code_search"


def test_fallback_node_empty_and_simple_payload_are_not_full_runtime() -> None:
    fallback = build_cognitive_runtime_inspection(**_base_kwargs(response="SAFE", last_runtime_mode="fallback"))
    assert fallback["runtime_truth"]["runtime_mode"] == "SAFE_FALLBACK"
    assert fallback["runtime_truth"]["runtime_mode"] != "FULL_COGNITIVE_RUNTIME"

    node_empty = build_cognitive_runtime_inspection(
        **_base_kwargs(
            response="NODE_FB",
            last_runtime_reason="empty_node_response",
            node_outcome={
                "semantic_lane": LANE_SAFE_DEGRADED_FALLBACK,
                "transport_status": TRANSPORT_FALLBACK,
                "reason_code": "empty_node_response",
                "exit_code": 0,
            },
        )
    )
    assert node_empty["runtime_truth"]["runtime_mode"] == "NODE_FALLBACK"

    simple_node = build_cognitive_runtime_inspection(
        **_base_kwargs(
            response="plain text",
            last_runtime_reason="direct_node_response",
            node_outcome={
                "semantic_lane": LANE_LOCAL_DIRECT_RESPONSE,
                "transport_status": TRANSPORT_SUCCESS,
                "reason_code": "direct_node_response",
                "has_execution_request": False,
            },
        )
    )
    assert simple_node["runtime_truth"]["runtime_mode"] == "RULE_BASED_INTENT"
    assert simple_node["runtime_truth"]["runtime_mode"] != "FULL_COGNITIVE_RUNTIME"


def test_memory_only_and_public_payload_contract() -> None:
    row = build_cognitive_runtime_inspection(
        **_base_kwargs(
            response="Seu nome é Misael.",
            direct_memory_hit=True,
            node_outcome={
                "semantic_lane": LANE_LOCAL_DIRECT_RESPONSE,
                "transport_status": TRANSPORT_SUCCESS,
                "runtime_truth": {"intent": "memory"},
            },
        )
    )
    assert row["runtime_truth"]["runtime_mode"] == "MEMORY_ONLY_RESPONSE"
    assert row["runtime_truth"]["llm_provider_succeeded"] is False

    raw = copy.deepcopy(row)
    raw["signals"]["execution_request"] = {"actions": [{"tool": "read_file"}]}
    raw["signals"]["stderr"] = "raw stderr"
    public = build_public_cognitive_runtime_inspection(raw)

    assert public["runtime_truth"]["runtime_mode"] == "MEMORY_ONLY_RESPONSE"
    assert public["runtime_truth"]["intent"] == "memory"
    assert _contains_key(public, "execution_request") is False
    assert _contains_key(public, "stderr") is False


def test_normalized_node_outcome_preserves_runtime_truth_classifier_metadata() -> None:
    node_outcome = normalize_node_outcome(
        transport_status=TRANSPORT_SUCCESS,
        semantic_lane=LANE_MATCHER_SHORTCUT,
        reason_code="direct_node_response",
        node_result_envelope={
            "response": "Olá!",
            "runtime_truth": {
                "intent": "greeting",
                "intent_source": "rule_based",
                "classifier_version": "regex_v1",
            },
        },
        response_text="Olá!",
    )

    assert node_outcome["runtime_truth"]["intent"] == "greeting"
    assert node_outcome["intent"] == "greeting"
    assert node_outcome["intent_source"] == "rule_based"
    assert node_outcome["classifier_version"] == "regex_v1"
