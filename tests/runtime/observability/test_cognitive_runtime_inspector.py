from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from brain.runtime.observability.cognitive_runtime_inspector import (
    RUNTIME_MODE_COMPAT,
    RUNTIME_MODE_FULL,
    RUNTIME_MODE_LOCAL_TOOL_SUCCESS,
    RUNTIME_MODE_LOCAL_DIRECT,
    RUNTIME_MODE_MATCHER,
    RUNTIME_MODE_NODE_FB,
    RUNTIME_MODE_NODE_OK,
    RUNTIME_MODE_PARTIAL,
    RUNTIME_MODE_PROVIDER_FAILURE,
    RUNTIME_MODE_SAFE_FB,
    VERDICT_DEGRADED,
    VERDICT_HYBRID,
    VERDICT_TRUE,
    build_cognitive_runtime_inspection,
)
from brain.runtime.observability.runtime_lane_classifier import (
    LANE_BRIDGE_EXECUTION_REQUEST,
    LANE_COMPATIBILITY_EXECUTION,
    LANE_LOCAL_DIRECT_RESPONSE,
    LANE_MATCHER_SHORTCUT,
    LANE_SAFE_DEGRADED_FALLBACK,
    LANE_TRUE_ACTION_EXECUTION,
    TRANSPORT_FALLBACK,
    TRANSPORT_SUCCESS,
)


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
        duration_ms=100,
    )
    base.update(overrides)
    return base


def test_node_fallback_is_degraded() -> None:
    row = build_cognitive_runtime_inspection(**_base_kwargs(response="NODE_FB", last_runtime_reason="timeout"))
    assert row["runtime_mode"] == RUNTIME_MODE_NODE_FB
    assert row["runtime_reason"] == "timeout"
    assert row["final_verdict"] == VERDICT_DEGRADED
    assert "node_failure" in row["detected_failures"][0]
    assert row["signals"]["semantic_runtime_lane"] == LANE_SAFE_DEGRADED_FALLBACK
    assert row["signals"]["transport_status"] == TRANSPORT_FALLBACK
    assert row["signals"]["fallback_triggered"] is True


def test_safe_fallback_is_degraded() -> None:
    row = build_cognitive_runtime_inspection(**_base_kwargs(response="SAFE", last_runtime_mode="fallback"))
    assert row["runtime_mode"] == RUNTIME_MODE_SAFE_FB
    assert row["signals"]["semantic_runtime_lane"] == LANE_SAFE_DEGRADED_FALLBACK
    assert row["signals"]["fallback_triggered"] is True


def test_matcher_shortcut_hybrid() -> None:
    row = build_cognitive_runtime_inspection(
        **_base_kwargs(
            response="hello",
            last_runtime_reason="direct_node_response",
            node_cognitive_hint={"lane": "matcher_shortcut"},
        )
    )
    assert row["runtime_mode"] == RUNTIME_MODE_MATCHER
    assert row["final_verdict"] == VERDICT_HYBRID
    assert row["source_of_truth"] == "Matcher"
    assert row["signals"]["semantic_runtime_lane"] == LANE_MATCHER_SHORTCUT
    assert row["signals"]["node_execution_successful"] is False


def test_full_path_strict() -> None:
    row = build_cognitive_runtime_inspection(**_base_kwargs())
    assert row["runtime_mode"] == RUNTIME_MODE_FULL
    assert row["cognitive_chain"] == "COMPLETE"
    assert row["final_verdict"] == VERDICT_TRUE
    assert row["signals"]["semantic_runtime_lane"] == LANE_TRUE_ACTION_EXECUTION
    assert row["signals"]["execution_runtime_lane"] == LANE_TRUE_ACTION_EXECUTION
    assert row["signals"]["compatibility_execution_active"] is False
    assert row["signals"]["node_execution_successful"] is True


def test_local_direct_response_lane_is_explicit() -> None:
    row = build_cognitive_runtime_inspection(
        **_base_kwargs(
            response="Seu nome é Misael.",
            last_runtime_reason="direct_node_response",
            node_outcome={
                "semantic_lane": LANE_LOCAL_DIRECT_RESPONSE,
                "transport_status": TRANSPORT_SUCCESS,
                "reason_code": "direct_node_response",
                "node_hint_lane": "no_tool_local",
            },
            lora_payload={
                "strategy_dispatch_applied": True,
                "executor_used": "direct_response_executor",
                "execution_trace_summary": "Direct response executor used the compatibility runtime path.",
            },
        )
    )
    assert row["runtime_mode"] == RUNTIME_MODE_LOCAL_DIRECT
    assert row["signals"]["semantic_runtime_lane"] == LANE_LOCAL_DIRECT_RESPONSE
    assert row["signals"]["execution_runtime_lane"] == LANE_COMPATIBILITY_EXECUTION
    assert row["signals"]["compatibility_execution_active"] is True
    assert row["final_verdict"] == VERDICT_HYBRID
    assert row["signals"]["execution_path_used"] == "node_execution"


def test_bridge_execution_request_lane_is_explicit() -> None:
    row = build_cognitive_runtime_inspection(
        **_base_kwargs(
            response="[execução_python_requerida] análise preparada",
            last_runtime_reason="node_response_without_actions",
            node_outcome={
                "semantic_lane": LANE_BRIDGE_EXECUTION_REQUEST,
                "transport_status": TRANSPORT_SUCCESS,
                "reason_code": "node_response_without_actions",
                "has_execution_request": True,
                "has_actions": False,
            },
            lora_payload={
                "strategy_dispatch_applied": True,
                "executor_used": "direct_response_executor",
                "execution_trace_summary": "Direct response executor used the compatibility runtime path.",
            },
        )
    )
    assert row["runtime_mode"] == RUNTIME_MODE_COMPAT
    assert row["signals"]["semantic_runtime_lane"] == LANE_BRIDGE_EXECUTION_REQUEST
    assert row["signals"]["execution_runtime_lane"] == LANE_COMPATIBILITY_EXECUTION
    assert row["signals"]["compatibility_execution_active"] is True
    assert row["final_verdict"] == VERDICT_HYBRID


def test_compatibility_execution_lane_is_explicit() -> None:
    row = build_cognitive_runtime_inspection(
        **_base_kwargs(
            response="Resposta local",
            last_runtime_reason="direct_python_response",
            node_outcome=None,
            direct_memory_hit=True,
            lora_payload={"strategy_dispatch_applied": True},
        )
    )
    assert row["runtime_mode"] == RUNTIME_MODE_COMPAT
    assert row["signals"]["semantic_runtime_lane"] == LANE_COMPATIBILITY_EXECUTION
    assert row["signals"]["execution_runtime_lane"] == LANE_COMPATIBILITY_EXECUTION
    assert row["signals"]["compatibility_execution_active"] is True
    assert row["final_verdict"] == VERDICT_HYBRID


def test_true_action_execution_is_not_equivalent_to_compatibility_execution() -> None:
    row = build_cognitive_runtime_inspection(
        **_base_kwargs(
            response="ok",
            last_runtime_reason="node_execution_request",
            node_outcome={
                "semantic_lane": LANE_TRUE_ACTION_EXECUTION,
                "transport_status": TRANSPORT_SUCCESS,
                "reason_code": "node_execution_request",
                "has_execution_request": True,
                "has_actions": True,
            },
            lora_payload={
                "strategy_dispatch_applied": True,
                "executor_used": "tool_assisted_executor",
                "execution_trace_summary": "Action executor completed with structured tool results.",
            },
        )
    )
    assert row["runtime_mode"] == RUNTIME_MODE_FULL
    assert row["signals"]["semantic_runtime_lane"] == LANE_TRUE_ACTION_EXECUTION
    assert row["signals"]["execution_runtime_lane"] == LANE_TRUE_ACTION_EXECUTION
    assert row["signals"]["compatibility_execution_active"] is False
    assert row["signals"]["node_execution_successful"] is True
    assert row["final_verdict"] == VERDICT_TRUE


def test_true_action_execution_overrides_compatibility_trace_when_explicitly_promoted() -> None:
    row = build_cognitive_runtime_inspection(
        **_base_kwargs(
            response='{"name":"omni"}',
            last_runtime_reason="node_execution_request",
            node_outcome={
                "semantic_lane": LANE_TRUE_ACTION_EXECUTION,
                "transport_status": TRANSPORT_SUCCESS,
                "reason_code": "node_execution_request",
                "has_execution_request": True,
                "has_actions": True,
                "actions_executed": True,
                "execution_runtime_lane": LANE_TRUE_ACTION_EXECUTION,
            },
            lora_payload={
                "strategy_dispatch_applied": True,
                "executor_used": "tool_assisted_executor",
                "execution_trace_summary": "Tool-assisted executor used the compatibility runtime path with manifest-selected tool metadata.",
                "execution_runtime_lane": LANE_TRUE_ACTION_EXECUTION,
                "compatibility_execution_active": False,
                "true_action_execution_active": True,
            },
        )
    )
    assert row["runtime_mode"] == RUNTIME_MODE_FULL
    assert row["signals"]["semantic_runtime_lane"] == LANE_TRUE_ACTION_EXECUTION
    assert row["signals"]["execution_runtime_lane"] == LANE_TRUE_ACTION_EXECUTION
    assert row["signals"]["compatibility_execution_active"] is False


def test_node_execution_success_without_full_chain_is_distinct() -> None:
    row = build_cognitive_runtime_inspection(
        **_base_kwargs(
            response="ok",
            last_runtime_reason="node_execution_request",
            planning_payload={"planning_trace": {"execution_ready": False}},
            node_outcome={
                "semantic_lane": LANE_TRUE_ACTION_EXECUTION,
                "transport_status": TRANSPORT_SUCCESS,
                "reason_code": "node_execution_request",
                "has_execution_request": True,
                "has_actions": True,
            },
            lora_payload={
                "strategy_dispatch_applied": True,
                "executor_used": "tool_assisted_executor",
                "execution_trace_summary": "Action executor completed with structured tool results.",
                "execution_path_used": "node_execution",
            },
        )
    )
    assert row["runtime_mode"] == RUNTIME_MODE_NODE_OK
    assert row["signals"]["node_execution_successful"] is True
    assert row["signals"]["execution_path_used"] == "node_execution"


def test_local_tool_success_is_explicit() -> None:
    row = build_cognitive_runtime_inspection(
        **_base_kwargs(
            response="Leitura concluída.",
            last_runtime_reason="local_tool_execution",
            node_outcome={
                "semantic_lane": LANE_LOCAL_DIRECT_RESPONSE,
                "transport_status": TRANSPORT_SUCCESS,
                "reason_code": "local_tool_execution",
                "node_hint_lane": "node_local_tool_run",
            },
            lora_payload={
                "strategy_dispatch_applied": True,
                "execution_runtime_lane": "local_tool_execution",
                "execution_path_used": "local_tool_execution",
                "compatibility_execution_active": False,
            },
        )
    )
    assert row["runtime_mode"] == RUNTIME_MODE_LOCAL_TOOL_SUCCESS
    assert row["signals"]["execution_runtime_lane"] == "local_tool_execution"
    assert row["signals"]["execution_path_used"] == "local_tool_execution"


def test_provider_failure_overrides_non_fallback_semantic_lane() -> None:
    row = build_cognitive_runtime_inspection(
        **_base_kwargs(
            response="Não consegui concluir a execução.",
            last_runtime_reason="provider_timeout",
            swarm_result={
                "metadata": {
                    "execution_provenance": {
                        "provider_actual": "openai",
                        "provider_failed": True,
                        "failure_class": "provider_timeout",
                    }
                }
            },
            node_outcome={
                "semantic_lane": LANE_TRUE_ACTION_EXECUTION,
                "transport_status": TRANSPORT_SUCCESS,
                "reason_code": "node_execution_request",
                "has_execution_request": True,
                "has_actions": True,
            },
            lora_payload={
                "strategy_dispatch_applied": True,
                "execution_path_used": "node_execution",
            },
        )
    )
    assert row["runtime_mode"] == RUNTIME_MODE_PROVIDER_FAILURE
    assert row["runtime_reason"] == "provider_timeout"
    assert row["signals"]["provider_actual"] == "openai"
    assert row["signals"]["provider_failed"] is True
    assert row["signals"]["failure_class"] == "provider_timeout"


def test_bridge_execution_request_without_compatibility_is_partial_runtime() -> None:
    row = build_cognitive_runtime_inspection(
        **_base_kwargs(
            response="[execução_python_requerida] análise preparada",
            last_runtime_reason="node_response_without_actions",
            node_outcome={
                "semantic_lane": LANE_BRIDGE_EXECUTION_REQUEST,
                "transport_status": TRANSPORT_SUCCESS,
                "reason_code": "node_response_without_actions",
                "has_execution_request": True,
                "has_actions": False,
            },
            lora_payload={
                "strategy_dispatch_applied": True,
                "execution_runtime_lane": LANE_BRIDGE_EXECUTION_REQUEST,
                "compatibility_execution_active": False,
                "execution_path_used": "node_execution",
            },
        )
    )
    assert row["runtime_mode"] == RUNTIME_MODE_PARTIAL
    assert row["signals"]["semantic_runtime_lane"] == LANE_BRIDGE_EXECUTION_REQUEST
    assert row["signals"]["execution_runtime_lane"] == LANE_BRIDGE_EXECUTION_REQUEST
