from __future__ import annotations

from typing import Any

RUNTIME_MODE_FULL_COGNITIVE_RUNTIME = "FULL_COGNITIVE_RUNTIME"
RUNTIME_MODE_PARTIAL_COGNITIVE_RUNTIME = "PARTIAL_COGNITIVE_RUNTIME"
RUNTIME_MODE_NODE_EXECUTION_SUCCESS = "NODE_EXECUTION_SUCCESS"
RUNTIME_MODE_LOCAL_TOOL_SUCCESS = "LOCAL_TOOL_SUCCESS"
RUNTIME_MODE_MATCHER_SHORTCUT = "MATCHER_SHORTCUT"
RUNTIME_MODE_DIRECT_LOCAL_RESPONSE = "DIRECT_LOCAL_RESPONSE"
RUNTIME_MODE_SAFE_FALLBACK = "SAFE_FALLBACK"
RUNTIME_MODE_NODE_FAILURE = "NODE_FAILURE"
RUNTIME_MODE_PROVIDER_FAILURE = "PROVIDER_FAILURE"
RUNTIME_MODE_COMPATIBILITY_EXECUTION = "COMPATIBILITY_EXECUTION"


RUNTIME_MODE_DEFINITIONS: dict[str, dict[str, Any]] = {
    RUNTIME_MODE_FULL_COGNITIVE_RUNTIME: {
        "meaning": "A real action-backed runtime completed with non-fallback execution and a complete cognitive chain.",
        "required_evidence": [
            "semantic_runtime_lane=true_action_execution",
            "execution_runtime_lane=true_action_execution",
            "compatibility_execution_active=false",
            "cognitive_chain=COMPLETE",
        ],
        "invalid_evidence": [
            "fallback_triggered=true",
            "compatibility_execution_active=true",
            "semantic_runtime_lane=matcher_shortcut",
        ],
        "example_source_path": "backend/python/brain/runtime/observability/cognitive_runtime_inspector.py",
    },
    RUNTIME_MODE_PARTIAL_COGNITIVE_RUNTIME: {
        "meaning": "The runtime produced a non-fallback result, but the evidence does not support full action-backed completion.",
        "required_evidence": [
            "non-empty response",
            "no explicit fallback or provider failure",
        ],
        "invalid_evidence": [
            "cognitive_chain=COMPLETE with true_action_execution",
            "fallback_triggered=true",
        ],
        "example_source_path": "backend/python/brain/runtime/observability/cognitive_runtime_inspector.py",
    },
    RUNTIME_MODE_NODE_EXECUTION_SUCCESS: {
        "meaning": "Node produced a successful action-backed result, but the turn does not satisfy the stricter full-runtime gate.",
        "required_evidence": [
            "semantic_runtime_lane=true_action_execution",
            "execution_path_used=node_execution",
            "transport_status=success",
        ],
        "invalid_evidence": [
            "compatibility_execution_active=true",
            "fallback_triggered=true",
        ],
        "example_source_path": "backend/python/brain/runtime/orchestrator.py",
    },
    RUNTIME_MODE_LOCAL_TOOL_SUCCESS: {
        "meaning": "A local tool branch executed successfully without degrading to compatibility fallback.",
        "required_evidence": [
            "execution_runtime_lane=local_tool_execution or node_hint_lane=node_local_tool_run",
            "transport_status=success or execution_path_used=local_tool_execution",
        ],
        "invalid_evidence": [
            "fallback_triggered=true",
            "compatibility_execution_active=true",
        ],
        "example_source_path": "backend/python/brain/runtime/orchestrator.py",
    },
    RUNTIME_MODE_MATCHER_SHORTCUT: {
        "meaning": "A matcher/shortcut answered the turn without executing a cognitive or tool path.",
        "required_evidence": [
            "semantic_runtime_lane=matcher_shortcut or node_hint_lane=matcher_shortcut",
        ],
        "invalid_evidence": [
            "execution_runtime_lane=true_action_execution",
        ],
        "example_source_path": "core/brain/queryEngineAuthority.js",
    },
    RUNTIME_MODE_DIRECT_LOCAL_RESPONSE: {
        "meaning": "Node or Python produced a local response without real action execution.",
        "required_evidence": [
            "semantic_runtime_lane=local_direct_response",
        ],
        "invalid_evidence": [
            "execution_runtime_lane=true_action_execution",
            "fallback_triggered=true",
        ],
        "example_source_path": "core/brain/queryEngineAuthority.js",
    },
    RUNTIME_MODE_SAFE_FALLBACK: {
        "meaning": "The runtime intentionally returned the safe fallback path.",
        "required_evidence": [
            "fallback_triggered=true or semantic_runtime_lane=safe_degraded_fallback",
            "safe fallback response or fallback runtime reason",
        ],
        "invalid_evidence": [
            "execution_runtime_lane=true_action_execution",
        ],
        "example_source_path": "backend/python/brain/runtime/orchestrator.py",
    },
    RUNTIME_MODE_NODE_FAILURE: {
        "meaning": "The Node path failed or returned an unusable payload.",
        "required_evidence": [
            "last_runtime_reason in node failure reasons or empty node response",
        ],
        "invalid_evidence": [
            "transport_status=success with true action execution",
        ],
        "example_source_path": "backend/python/brain/runtime/node_transport.py",
    },
    RUNTIME_MODE_PROVIDER_FAILURE: {
        "meaning": "Provider selection or provider-backed execution failed and that failure is explicitly evidenced.",
        "required_evidence": [
            "execution_provenance.provider_failed=true or failure_class indicates provider failure",
        ],
        "invalid_evidence": [
            "only a generic fallback reason without provider evidence",
        ],
        "example_source_path": "core/brain/executionProvenance.js",
    },
    RUNTIME_MODE_COMPATIBILITY_EXECUTION: {
        "meaning": "The turn was completed through the compatibility runtime path. It is supported, but it is not the true action-backed happy path.",
        "required_evidence": [
            "compatibility_execution_active=true or execution_runtime_lane=compatibility_execution",
        ],
        "invalid_evidence": [
            "execution_runtime_lane=true_action_execution",
        ],
        "example_source_path": "backend/python/brain/runtime/execution/strategy_dispatcher.py",
    },
}
