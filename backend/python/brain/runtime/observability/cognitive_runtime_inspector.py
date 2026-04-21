"""Conservative inspection of a single Omni turn — operational truth, not design intent."""

from __future__ import annotations

import os
from typing import Any

# Align with orchestrator-facing semantics (strict / conservative).
RUNTIME_MODE_FULL = "FULL_COGNITIVE_RUNTIME"
RUNTIME_MODE_PARTIAL = "PARTIAL_COGNITIVE"
RUNTIME_MODE_NODE_OK = "NODE_EXECUTION_SUCCESS"
RUNTIME_MODE_MATCHER = "MATCHER_SHORTCUT"
RUNTIME_MODE_SAFE_FB = "SAFE_FALLBACK"
RUNTIME_MODE_NODE_FB = "NODE_FALLBACK"
RUNTIME_MODE_ERROR_DEGRADED = "ERROR_DEGRADED"

CHAIN_COMPLETE = "COMPLETE"
CHAIN_PARTIAL = "PARTIAL"
CHAIN_BROKEN = "BROKEN"

SOURCE_PYTHON = "Python"
SOURCE_NODE = "Node"
SOURCE_MATCHER = "Matcher"
SOURCE_FALLBACK = "Fallback"

MEM_ACTIVE = "ACTIVE"
MEM_PASSIVE = "PASSIVE"
MEM_UNUSED = "UNUSED"

VERDICT_TRUE = "TRUE_COGNITIVE_RUNTIME"
VERDICT_DEGRADED = "DEGRADED_SYSTEM"
VERDICT_HYBRID = "HYBRID_UNSTABLE"


def _truthy_env(name: str) -> bool:
    return str(os.getenv(name, "")).strip().lower() in ("1", "true", "yes")


def _reasoning_validation(reasoning_payload: dict[str, Any] | None) -> str:
    if not isinstance(reasoning_payload, dict):
        return ""
    tr = reasoning_payload.get("trace")
    if not isinstance(tr, dict):
        return ""
    return str(tr.get("validation_result", "") or "").strip().lower()


def _strategy_degraded(strategy_payload: dict[str, Any] | None) -> bool:
    if not isinstance(strategy_payload, dict):
        return False
    return bool(strategy_payload.get("degraded"))


def _memory_class(memory_context_payload: dict[str, Any] | None, direct_memory_hit: bool) -> str:
    if direct_memory_hit:
        return MEM_ACTIVE
    if not isinstance(memory_context_payload, dict):
        return MEM_UNUSED
    try:
        n = int(memory_context_payload.get("selected_count", 0) or 0)
    except (TypeError, ValueError):
        n = 0
    if n > 0:
        return MEM_ACTIVE
    if memory_context_payload.get("sources_used"):
        return MEM_PASSIVE
    return MEM_UNUSED


def _evolution_status(self_improving_trace: dict[str, Any] | None) -> str:
    if _truthy_env("OMINI_PHASE40_DISABLE"):
        return "disabled"
    if not isinstance(self_improving_trace, dict):
        return "idle"
    if self_improving_trace.get("disabled"):
        return "disabled"
    if not _truthy_env("OMINI_PHASE40_ENABLE"):
        return "idle"
    if self_improving_trace.get("idle"):
        return "idle"
    return "active"


def _evolution_applied_summary(
    self_improving_trace: dict[str, Any] | None,
    controlled_evolution: dict[str, Any] | None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "phase40_env_enable": _truthy_env("OMINI_PHASE40_ENABLE"),
        "phase40_env_apply": _truthy_env("OMINI_PHASE40_APPLY"),
        "phase40_env_disable": _truthy_env("OMINI_PHASE40_DISABLE"),
        "cycle_rollout_stage": "",
        "approval_decision": "",
        "simulation_ran": False,
        "proposal_count": 0,
    }
    if isinstance(self_improving_trace, dict):
        out["cycle_rollout_stage"] = str(self_improving_trace.get("rollout_stage") or "")
        out["approval_decision"] = str(self_improving_trace.get("approval_decision") or "")
        cyc = self_improving_trace.get("cycle")
        if isinstance(cyc, dict):
            out["simulation_ran"] = bool(cyc.get("simulation_result"))
    if isinstance(controlled_evolution, dict):
        try:
            out["proposal_count"] = int(controlled_evolution.get("proposal_count") or 0)
        except (TypeError, ValueError):
            out["proposal_count"] = 0
        out["simulation_ran"] = out["simulation_ran"] or bool(controlled_evolution.get("opportunities"))
    return out


def build_cognitive_runtime_inspection(
    *,
    response: str,
    safe_fallback: str,
    node_fallback: str,
    mock_response: str,
    last_runtime_mode: str,
    last_runtime_reason: str,
    reasoning_payload: dict[str, Any] | None,
    strategy_payload: dict[str, Any] | None,
    memory_context_payload: dict[str, Any] | None,
    planning_payload: dict[str, Any] | None,
    swarm_result: dict[str, Any] | None,
    learning_record: dict[str, Any] | None,
    node_cognitive_hint: dict[str, Any] | None,
    direct_memory_hit: bool,
    self_improving_system_trace: dict[str, Any] | None,
    controlled_evolution_payload: dict[str, Any] | None,
    coordination_payload: dict[str, Any] | None,
    lora_payload: dict[str, Any] | None,
    duration_ms: int,
) -> dict[str, Any]:
    r = str(response or "").strip()
    safe = str(safe_fallback or "").strip()
    node_fb = str(node_fallback or "").strip()
    mock = str(mock_response or "").strip()

    failures: list[str] = []
    perf_notes: list[str] = []

    validation = _reasoning_validation(reasoning_payload)
    strat_deg = _strategy_degraded(strategy_payload)
    mem_usage = _memory_class(memory_context_payload, direct_memory_hit)

    hint_lane = ""
    if isinstance(node_cognitive_hint, dict):
        hint_lane = str(node_cognitive_hint.get("lane") or node_cognitive_hint.get("detail") or "").strip().lower()

    node_matcher = hint_lane in {"matcher_shortcut", "conversational_matcher"} or "matcher" in hint_lane

    learning_path = ""
    if isinstance(learning_record, dict):
        assess = learning_record.get("assessment")
        if isinstance(assess, dict):
            learning_path = str(assess.get("execution_path") or "")

    if r == node_fb:
        runtime_mode = RUNTIME_MODE_NODE_FB
        source = SOURCE_FALLBACK
        failures.append("node_path_unusable_or_subprocess_failure")
    elif r == safe:
        runtime_mode = RUNTIME_MODE_SAFE_FB
        source = SOURCE_FALLBACK
        failures.append("safe_fallback_template_or_empty_operational_path")
    elif r == mock:
        runtime_mode = RUNTIME_MODE_ERROR_DEGRADED
        source = SOURCE_FALLBACK
        failures.append("mock_runtime_configured")
    elif node_matcher:
        runtime_mode = RUNTIME_MODE_MATCHER
        source = SOURCE_MATCHER
        failures.append("matcher_shortcut_bypassed_llm_grounding")
    elif direct_memory_hit:
        runtime_mode = RUNTIME_MODE_PARTIAL
        source = SOURCE_PYTHON
    elif last_runtime_reason == "node_execution_request" and last_runtime_mode == "live":
        runtime_mode = RUNTIME_MODE_NODE_OK
        source = SOURCE_NODE
    elif last_runtime_mode == "fallback":
        runtime_mode = RUNTIME_MODE_ERROR_DEGRADED
        if last_runtime_reason in {"control_layer_block", "reasoning_validation_block"}:
            source = SOURCE_PYTHON
        else:
            source = SOURCE_FALLBACK
        failures.append(f"runtime_fallback_mode_or_reason:{last_runtime_reason}")
    elif last_runtime_reason in {"direct_node_response", "node_response_without_actions"} and last_runtime_mode == "live":
        runtime_mode = RUNTIME_MODE_NODE_OK
        source = SOURCE_NODE
    else:
        runtime_mode = RUNTIME_MODE_PARTIAL
        source = SOURCE_NODE if learning_path == "swarm" else SOURCE_PYTHON

    if validation in {"invalid", "fallback"}:
        failures.append(f"reasoning_validation:{validation or 'unknown'}")
    if strat_deg:
        failures.append("strategy_engine_degraded")
    if isinstance(coordination_payload, dict):
        tr = coordination_payload.get("trace")
        if isinstance(tr, dict) and tr.get("degraded"):
            failures.append("coordination_trace_degraded")
        hb = coordination_payload.get("handoff_bundle")
        if isinstance(hb, dict) and hb.get("fallback"):
            failures.append("coordination_handoff_fallback")

    # Cognitive chain (strict).
    strat_ok = isinstance(strategy_payload, dict) and strategy_payload and not strat_deg
    reason_ok = validation == "valid"
    plan_ok = False
    if isinstance(planning_payload, dict):
        pt = planning_payload.get("planning_trace")
        if isinstance(pt, dict) and pt.get("execution_ready"):
            plan_ok = True

    node_graph = last_runtime_reason == "node_execution_request" and last_runtime_mode == "live"
    node_soft = last_runtime_mode == "live" and last_runtime_reason in {
        "direct_node_response",
        "node_response_without_actions",
    }
    tools_or_sim = node_graph and not node_matcher

    chain_parts = {
        "strategy_generation": strat_ok,
        "reasoning_trace_oil": reason_ok,
        "execution_graph_node": bool(node_graph or node_soft),
        "tool_usage_or_simulation": bool(tools_or_sim),
        "structured_synthesis": bool(r) and r not in {safe, node_fb, mock},
    }
    if node_matcher:
        chain_parts["tool_usage_or_simulation"] = False
        chain_parts["execution_graph_node"] = False

    complete = all(chain_parts.values())
    if complete:
        cognitive_chain = CHAIN_COMPLETE
    elif any(chain_parts.values()):
        cognitive_chain = CHAIN_PARTIAL
    else:
        cognitive_chain = CHAIN_BROKEN

    if runtime_mode in (RUNTIME_MODE_NODE_FB, RUNTIME_MODE_SAFE_FB, RUNTIME_MODE_ERROR_DEGRADED):
        cognitive_chain = CHAIN_BROKEN

    # Performance heuristics.
    if direct_memory_hit:
        perf_notes.append("swarm_node_skipped_due_to_direct_memory_hit")
    elif learning_path == "swarm" and reason_ok and strat_ok:
        perf_notes.append("python_reasoning_strategy_then_node_planner_likely_redundant_work")

    if duration_ms > 45_000:
        perf_notes.append("high_latency_risk_subprocess_and_dual_runtime")

    # FULL only if chain complete, non-matcher, non-fallback, live mode, swarm path used tools graph.
    if (
        runtime_mode == RUNTIME_MODE_NODE_OK
        and cognitive_chain == CHAIN_COMPLETE
        and last_runtime_mode == "live"
        and not node_matcher
        and not direct_memory_hit
        and tools_or_sim
    ):
        runtime_mode = RUNTIME_MODE_FULL

    # Final verdict (conservative).
    if runtime_mode in (RUNTIME_MODE_NODE_FB, RUNTIME_MODE_SAFE_FB, RUNTIME_MODE_ERROR_DEGRADED):
        verdict = VERDICT_DEGRADED
    elif runtime_mode == RUNTIME_MODE_MATCHER or validation in {"invalid", "fallback"} or strat_deg:
        verdict = VERDICT_HYBRID
    elif runtime_mode == RUNTIME_MODE_FULL and cognitive_chain == CHAIN_COMPLETE:
        verdict = VERDICT_TRUE
    else:
        verdict = VERDICT_HYBRID

    if mem_usage == MEM_UNUSED and not direct_memory_hit:
        failures.append("memory_intelligence_unused_for_turn")

    evo = _evolution_status(self_improving_system_trace)
    evo_detail = _evolution_applied_summary(self_improving_system_trace, controlled_evolution_payload)
    lora_signals: dict[str, Any] = {}
    if isinstance(lora_payload, dict):
        lora_signals = {
            "lora_used": bool(lora_payload.get("lora_used", False)),
            "model_confidence": float(lora_payload.get("model_confidence", 0.0) or 0.0),
            "decision_source": str(lora_payload.get("decision_source", "rule") or "rule"),
            "dataset_origin": str(lora_payload.get("dataset_origin", "") or ""),
        }

    return {
        "runtime_mode": runtime_mode,
        "cognitive_chain": cognitive_chain,
        "cognitive_chain_steps": chain_parts,
        "source_of_truth": source,
        "memory_usage": mem_usage,
        "detected_failures": failures,
        "performance_notes": "; ".join(perf_notes) if perf_notes else "no_extra_signals",
        "evolution_status": evo,
        "evolution_detail": evo_detail,
        "final_verdict": verdict,
        "signals": {
            "last_runtime_mode": str(last_runtime_mode or ""),
            "last_runtime_reason": str(last_runtime_reason or ""),
            "reasoning_validation": validation or "unknown",
            "direct_memory_hit": bool(direct_memory_hit),
            "learning_execution_path": learning_path or "unknown",
            "node_cognitive_hint": node_cognitive_hint if isinstance(node_cognitive_hint, dict) else None,
            "duration_ms": int(duration_ms),
            **lora_signals,
        },
    }
