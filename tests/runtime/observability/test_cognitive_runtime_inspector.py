from __future__ import annotations

from brain.runtime.observability.cognitive_runtime_inspector import (
    RUNTIME_MODE_FULL,
    RUNTIME_MODE_MATCHER,
    RUNTIME_MODE_NODE_FB,
    RUNTIME_MODE_SAFE_FB,
    VERDICT_DEGRADED,
    VERDICT_HYBRID,
    VERDICT_TRUE,
    build_cognitive_runtime_inspection,
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
    assert row["final_verdict"] == VERDICT_DEGRADED
    assert "node_path_unusable" in row["detected_failures"][0]


def test_safe_fallback_is_degraded() -> None:
    row = build_cognitive_runtime_inspection(**_base_kwargs(response="SAFE", last_runtime_mode="fallback"))
    assert row["runtime_mode"] == RUNTIME_MODE_SAFE_FB


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


def test_full_path_strict() -> None:
    row = build_cognitive_runtime_inspection(**_base_kwargs())
    assert row["runtime_mode"] == RUNTIME_MODE_FULL
    assert row["cognitive_chain"] == "COMPLETE"
    assert row["final_verdict"] == VERDICT_TRUE
