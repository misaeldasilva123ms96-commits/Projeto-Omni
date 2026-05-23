from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.observability.runtime_lane_classifier import (
    LANE_BRIDGE_EXECUTION_REQUEST,
    LANE_COMPATIBILITY_EXECUTION,
    LANE_LOCAL_DIRECT_RESPONSE,
    LANE_MATCHER_SHORTCUT,
    LANE_SAFE_DEGRADED_FALLBACK,
    LANE_TRUE_ACTION_EXECUTION,
    TRANSPORT_FALLBACK,
    TRANSPORT_SUCCESS,
    classify_execution_runtime_lane,
    classify_runtime_lane,
    interpret_node_payload,
    normalize_node_outcome,
)


def test_normalize_node_outcome_tracks_actions_and_response() -> None:
    row = normalize_node_outcome(
        transport_status=TRANSPORT_SUCCESS,
        semantic_lane=LANE_TRUE_ACTION_EXECUTION,
        reason_code="node_execution_request",
        node_cognitive_hint={"lane": "node_execution_graph"},
        node_result_envelope={
            "response": "ok",
            "execution_request": {"actions": [{"tool": "read_file"}]},
        },
        response_text="ok",
    )
    assert row["semantic_lane"] == LANE_TRUE_ACTION_EXECUTION
    assert row["has_execution_request"] is True
    assert row["has_actions"] is True
    assert row["response_present"] is True
    assert row["node_hint_lane"] == "node_execution_graph"
    assert row["provider_actual"] == ""
    assert row["provider_failed"] is False


def test_classify_runtime_lane_prefers_matcher_shortcut() -> None:
    row = classify_runtime_lane(
        response="Olá!",
        safe_fallback="SAFE",
        node_fallback="NODE_FB",
        mock_response="MOCK",
        last_runtime_mode="live",
        last_runtime_reason="direct_node_response",
        node_cognitive_hint={"lane": "matcher_shortcut"},
        node_outcome=None,
        direct_memory_hit=False,
        strategy_dispatch_applied=True,
    )
    assert row["semantic_lane"] == LANE_MATCHER_SHORTCUT


def test_classify_runtime_lane_respects_local_direct_response() -> None:
    row = classify_runtime_lane(
        response="Seu nome é Misael.",
        safe_fallback="SAFE",
        node_fallback="NODE_FB",
        mock_response="MOCK",
        last_runtime_mode="live",
        last_runtime_reason="direct_node_response",
        node_cognitive_hint={"lane": "no_tool_local"},
        node_outcome=normalize_node_outcome(
            transport_status=TRANSPORT_SUCCESS,
            semantic_lane=LANE_LOCAL_DIRECT_RESPONSE,
            reason_code="direct_node_response",
            node_cognitive_hint={"lane": "no_tool_local"},
            node_result_envelope={"response": "Seu nome é Misael."},
            response_text="Seu nome é Misael.",
        ),
        direct_memory_hit=False,
        strategy_dispatch_applied=True,
    )
    assert row["semantic_lane"] == LANE_LOCAL_DIRECT_RESPONSE
    assert row["transport_status"] == TRANSPORT_SUCCESS


def test_classify_runtime_lane_respects_bridge_execution_request() -> None:
    row = classify_runtime_lane(
        response="[execução_python_requerida] análise preparada",
        safe_fallback="SAFE",
        node_fallback="NODE_FB",
        mock_response="MOCK",
        last_runtime_mode="live",
        last_runtime_reason="node_response_without_actions",
        node_cognitive_hint={"lane": "node_execution_graph"},
        node_outcome=normalize_node_outcome(
            transport_status=TRANSPORT_SUCCESS,
            semantic_lane=LANE_BRIDGE_EXECUTION_REQUEST,
            reason_code="node_response_without_actions",
            node_cognitive_hint={"lane": "node_execution_graph"},
            node_result_envelope={
                "response": "[execução_python_requerida] análise preparada",
                "execution_request": {"actions": []},
            },
            response_text="[execução_python_requerida] análise preparada",
        ),
        direct_memory_hit=False,
        strategy_dispatch_applied=True,
    )
    assert row["semantic_lane"] == LANE_BRIDGE_EXECUTION_REQUEST


def test_classify_runtime_lane_marks_compatibility_execution_without_node_outcome() -> None:
    row = classify_runtime_lane(
        response="Resposta local",
        safe_fallback="SAFE",
        node_fallback="NODE_FB",
        mock_response="MOCK",
        last_runtime_mode="live",
        last_runtime_reason="direct_python_response",
        node_cognitive_hint=None,
        node_outcome=None,
        direct_memory_hit=True,
        strategy_dispatch_applied=True,
    )
    assert row["semantic_lane"] == LANE_COMPATIBILITY_EXECUTION


def test_classify_runtime_lane_marks_safe_degraded_fallback() -> None:
    row = classify_runtime_lane(
        response="NODE_FB",
        safe_fallback="SAFE",
        node_fallback="NODE_FB",
        mock_response="MOCK",
        last_runtime_mode="fallback",
        last_runtime_reason="timeout",
        node_cognitive_hint=None,
        node_outcome=None,
        direct_memory_hit=False,
        strategy_dispatch_applied=False,
    )
    assert row["semantic_lane"] == LANE_SAFE_DEGRADED_FALLBACK
    assert row["transport_status"] == TRANSPORT_FALLBACK


def test_interpret_node_payload_derives_matcher_from_metadata_provenance() -> None:
    row = interpret_node_payload(
        parsed={
            "response": "Olá! Sou o Omni.",
            "metadata": {
                "execution_provenance": {
                    "execution_mode": "matcher_shortcut",
                }
            },
        },
        stdout='{"response":"Olá! Sou o Omni."}',
    )
    assert row["fallback"] is False
    assert row["semantic_lane"] == LANE_MATCHER_SHORTCUT
    assert row["node_cognitive_hint"] == {"lane": "matcher_shortcut"}
    assert row["reason_code"] == "direct_node_response"
    assert row["node_outcome"]["provider_actual"] == ""


def test_interpret_node_payload_bridge_without_actions() -> None:
    row = interpret_node_payload(
        parsed={
            "response": "[execução_python_requerida] plano pronto",
            "execution_request": {"actions": []},
            "metadata": {"execution_provenance": {"execution_mode": "python_executor_bridge"}},
        },
        stdout="x",
    )
    assert row["fallback"] is False
    assert row["semantic_lane"] == LANE_BRIDGE_EXECUTION_REQUEST
    assert row["reason_code"] == "node_response_without_actions"


def test_interpret_node_payload_bridge_from_hint_without_execution_request() -> None:
    row = interpret_node_payload(
        parsed={
            "response": "[execução_python_requerida] plano pronto",
            "metadata": {"execution_provenance": {"execution_mode": "python_executor_bridge"}},
        },
        stdout="x",
    )
    assert row["fallback"] is False
    assert row["semantic_lane"] == LANE_BRIDGE_EXECUTION_REQUEST
    assert row["reason_code"] == "direct_node_response"


def test_interpret_node_payload_action_execution() -> None:
    row = interpret_node_payload(
        parsed={
            "response": "ok",
            "execution_request": {"actions": [{"tool": "read_file"}]},
            "metadata": {"execution_provenance": {"provider_actual": "openai"}},
        },
        stdout="x",
    )
    assert row["fallback"] is False
    assert row["semantic_lane"] == LANE_TRUE_ACTION_EXECUTION
    assert row["reason_code"] == "node_execution_request"
    assert row["node_outcome"]["provider_actual"] == "openai"


def test_interpret_node_payload_empty_response_becomes_fallback() -> None:
    row = interpret_node_payload(
        parsed={},
        stdout="",
    )
    assert row["fallback"] is True
    assert row["semantic_lane"] == LANE_SAFE_DEGRADED_FALLBACK
    assert row["reason_code"] == "empty_node_response"


def test_normalize_node_outcome_tracks_provider_failure_from_provenance() -> None:
    row = normalize_node_outcome(
        transport_status=TRANSPORT_SUCCESS,
        semantic_lane=LANE_TRUE_ACTION_EXECUTION,
        reason_code="node_execution_request",
        node_result_envelope={
            "response": "provider failed",
            "metadata": {
                "execution_provenance": {
                    "provider_actual": "openai",
                    "provider_failed": True,
                    "failure_class": "provider_timeout",
                }
            },
        },
        response_text="provider failed",
    )
    assert row["provider_actual"] == "openai"
    assert row["provider_failed"] is True
    assert row["failure_class"] == "provider_timeout"


def test_classify_execution_runtime_lane_marks_compatibility_path_explicitly() -> None:
    row = classify_execution_runtime_lane(
        semantic_lane=LANE_LOCAL_DIRECT_RESPONSE,
        direct_memory_hit=False,
        strategy_dispatch_applied=True,
        executor_used="direct_response_executor",
        execution_trace_summary="Direct response executor used the compatibility runtime path.",
    )
    assert row["execution_runtime_lane"] == LANE_COMPATIBILITY_EXECUTION
    assert row["compatibility_execution_active"] is True


def test_classify_execution_runtime_lane_keeps_true_action_distinct() -> None:
    row = classify_execution_runtime_lane(
        semantic_lane=LANE_TRUE_ACTION_EXECUTION,
        direct_memory_hit=False,
        strategy_dispatch_applied=True,
        executor_used="tool_assisted_executor",
        execution_trace_summary="Action executor completed with structured tool results.",
    )
    assert row["execution_runtime_lane"] == LANE_TRUE_ACTION_EXECUTION
    assert row["compatibility_execution_active"] is False


def test_classify_execution_runtime_lane_promotes_explicit_true_action_over_compatibility() -> None:
    row = classify_execution_runtime_lane(
        semantic_lane=LANE_TRUE_ACTION_EXECUTION,
        direct_memory_hit=False,
        strategy_dispatch_applied=True,
        executor_used="tool_assisted_executor",
        execution_trace_summary="Tool-assisted executor used the compatibility runtime path with manifest-selected tool metadata.",
        explicit_execution_runtime_lane=LANE_TRUE_ACTION_EXECUTION,
        actions_executed=True,
    )
    assert row["execution_runtime_lane"] == LANE_TRUE_ACTION_EXECUTION
    assert row["compatibility_execution_active"] is False
