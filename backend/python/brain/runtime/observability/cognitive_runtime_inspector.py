"""Conservative inspection of a single Omni turn — operational truth, not design intent."""

from __future__ import annotations

import os
from typing import Any

from brain.runtime.error_taxonomy import OmniErrorCode, build_public_error
from brain.runtime.observability.runtime_lane_classifier import (
    LANE_BRIDGE_EXECUTION_REQUEST,
    LANE_COMPATIBILITY_EXECUTION,
    LANE_LOCAL_DIRECT_RESPONSE,
    LANE_MATCHER_SHORTCUT,
    LANE_SAFE_DEGRADED_FALLBACK,
    LANE_TRUE_ACTION_EXECUTION,
    TRANSPORT_SUCCESS,
    classify_execution_runtime_lane,
    classify_runtime_lane,
)
from brain.runtime.observability.runtime_modes import (
    RUNTIME_MODE_COMPATIBILITY_EXECUTION,
    RUNTIME_MODE_DEFINITIONS,
    RUNTIME_MODE_DIRECT_LOCAL_RESPONSE,
    RUNTIME_MODE_FULL_COGNITIVE_RUNTIME,
    RUNTIME_MODE_LOCAL_TOOL_SUCCESS,
    RUNTIME_MODE_MATCHER_SHORTCUT,
    RUNTIME_MODE_NODE_EXECUTION_SUCCESS,
    RUNTIME_MODE_NODE_FAILURE,
    RUNTIME_MODE_PARTIAL_COGNITIVE_RUNTIME,
    RUNTIME_MODE_PROVIDER_FAILURE,
    RUNTIME_MODE_SAFE_FALLBACK,
)

# Backward-compatible aliases for existing imports/tests.
RUNTIME_MODE_FULL = RUNTIME_MODE_FULL_COGNITIVE_RUNTIME
RUNTIME_MODE_PARTIAL = RUNTIME_MODE_PARTIAL_COGNITIVE_RUNTIME
RUNTIME_MODE_NODE_OK = RUNTIME_MODE_NODE_EXECUTION_SUCCESS
RUNTIME_MODE_MATCHER = RUNTIME_MODE_MATCHER_SHORTCUT
RUNTIME_MODE_LOCAL_DIRECT = RUNTIME_MODE_DIRECT_LOCAL_RESPONSE
RUNTIME_MODE_COMPAT = RUNTIME_MODE_COMPATIBILITY_EXECUTION
RUNTIME_MODE_SAFE_FB = RUNTIME_MODE_SAFE_FALLBACK
RUNTIME_MODE_NODE_FB = RUNTIME_MODE_NODE_FAILURE
RUNTIME_MODE_ACTION = RUNTIME_MODE_NODE_EXECUTION_SUCCESS
RUNTIME_MODE_BRIDGE = RUNTIME_MODE_PARTIAL_COGNITIVE_RUNTIME
RUNTIME_MODE_ERROR_DEGRADED = RUNTIME_MODE_SAFE_FALLBACK

TRUTH_MODE_FULL_COGNITIVE_RUNTIME = "FULL_COGNITIVE_RUNTIME"
TRUTH_MODE_PARTIAL_COGNITIVE = "PARTIAL_COGNITIVE"
TRUTH_MODE_MATCHER_SHORTCUT = "MATCHER_SHORTCUT"
TRUTH_MODE_RULE_BASED_INTENT = "RULE_BASED_INTENT"
TRUTH_MODE_SAFE_FALLBACK = "SAFE_FALLBACK"
TRUTH_MODE_NODE_FALLBACK = "NODE_FALLBACK"
TRUTH_MODE_PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
TRUTH_MODE_TOOL_BLOCKED = "TOOL_BLOCKED"
TRUTH_MODE_TOOL_EXECUTED = "TOOL_EXECUTED"
TRUTH_MODE_MEMORY_ONLY_RESPONSE = "MEMORY_ONLY_RESPONSE"

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


def _truth_public_summary(runtime_mode: str) -> str:
    if runtime_mode == TRUTH_MODE_MATCHER_SHORTCUT:
        return "Responded using a local pattern matcher. No AI provider was used."
    if runtime_mode == TRUTH_MODE_SAFE_FALLBACK:
        return "System operated in safe fallback mode due to runtime constraints."
    if runtime_mode == TRUTH_MODE_FULL_COGNITIVE_RUNTIME:
        return "Full cognitive execution with provider and tool verification."
    if runtime_mode == TRUTH_MODE_TOOL_EXECUTED:
        return "A real tool/action executed successfully."
    if runtime_mode == TRUTH_MODE_TOOL_BLOCKED:
        return "A requested tool/action was blocked by policy."
    if runtime_mode == TRUTH_MODE_PROVIDER_UNAVAILABLE:
        return "No usable LLM provider completed this turn."
    if runtime_mode == TRUTH_MODE_NODE_FALLBACK:
        return "Node runtime did not produce a usable execution result."
    if runtime_mode == TRUTH_MODE_MEMORY_ONLY_RESPONSE:
        return "Responded from memory/context without provider execution."
    return f"Execution completed in {runtime_mode or 'unknown'} mode."


def _truth_tool_status(tool_execution: dict[str, Any] | None) -> str:
    if not isinstance(tool_execution, dict):
        return "not_invoked"
    if bool(tool_execution.get("tool_denied")):
        return "blocked"
    if bool(tool_execution.get("tool_succeeded")):
        return "executed"
    if bool(tool_execution.get("tool_failed")):
        return "failed"
    if bool(tool_execution.get("tool_attempted")):
        return "attempted"
    if tool_execution.get("tool_selected") or tool_execution.get("tool_requested"):
        return "invoked"
    return "not_invoked"


def _truth_error_code(runtime_mode: str) -> str:
    return {
        TRUTH_MODE_MATCHER_SHORTCUT: OmniErrorCode.MATCHER_SHORTCUT_USED.value,
        TRUTH_MODE_RULE_BASED_INTENT: OmniErrorCode.RULE_BASED_INTENT_USED.value,
        TRUTH_MODE_PROVIDER_UNAVAILABLE: OmniErrorCode.PROVIDER_UNAVAILABLE.value,
        TRUTH_MODE_NODE_FALLBACK: OmniErrorCode.NODE_EMPTY_RESPONSE.value,
        TRUTH_MODE_TOOL_BLOCKED: OmniErrorCode.TOOL_BLOCKED_BY_GOVERNANCE.value,
    }.get(runtime_mode, "")


def _extract_execution_provenance(
    swarm_result: dict[str, Any] | None,
    lora_payload: dict[str, Any] | None,
    node_outcome: dict[str, Any] | None,
) -> dict[str, Any]:
    if isinstance(lora_payload, dict):
        ep = lora_payload.get("execution_provenance")
        if isinstance(ep, dict):
            return dict(ep)
        trace = lora_payload.get("trace")
        if isinstance(trace, dict) and isinstance(trace.get("execution_provenance"), dict):
            return dict(trace.get("execution_provenance"))
    if isinstance(swarm_result, dict):
        md = swarm_result.get("metadata")
        if isinstance(md, dict) and isinstance(md.get("execution_provenance"), dict):
            return dict(md.get("execution_provenance"))
        top = swarm_result.get("execution_provenance")
        if isinstance(top, dict):
            return dict(top)
    if isinstance(node_outcome, dict):
        provider_actual = str(node_outcome.get("provider_actual") or "").strip().lower()
        failure_class = str(node_outcome.get("failure_class") or "").strip().lower()
        provider_failed = bool(node_outcome.get("provider_failed", False))
        if provider_actual or failure_class or provider_failed:
            return {
                "provider_actual": provider_actual,
                "failure_class": failure_class,
                "provider_failed": provider_failed,
            }
    return {}


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
    node_outcome: dict[str, Any] | None,
    direct_memory_hit: bool,
    self_improving_system_trace: dict[str, Any] | None,
    controlled_evolution_payload: dict[str, Any] | None,
    coordination_payload: dict[str, Any] | None,
    lora_payload: dict[str, Any] | None = None,
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
    execution_provenance = _extract_execution_provenance(swarm_result, lora_payload, node_outcome)
    provider_actual = str(execution_provenance.get("provider_actual") or "").strip().lower()
    failure_class = str(execution_provenance.get("failure_class") or "").strip().lower()
    failure_reason = str(execution_provenance.get("failure_reason") or "").strip()
    provider_failed = bool(execution_provenance.get("provider_failed", False)) or failure_class.startswith("provider_")
    provider_diagnostics = execution_provenance.get("provider_diagnostics")
    if not isinstance(provider_diagnostics, list):
        provider_diagnostics = []
    provider_fallback_occurred = bool(execution_provenance.get("provider_fallback_occurred", False))
    no_provider_available = bool(execution_provenance.get("no_provider_available", False))
    tool_execution = None
    tool_diagnostics: list[dict[str, Any]] = []
    if isinstance(lora_payload, dict):
        maybe_tool_execution = lora_payload.get("tool_execution")
        if isinstance(maybe_tool_execution, dict):
            tool_execution = dict(maybe_tool_execution)
        maybe_tool_diagnostics = lora_payload.get("tool_diagnostics")
        if isinstance(maybe_tool_diagnostics, list):
            tool_diagnostics = [dict(item) for item in maybe_tool_diagnostics if isinstance(item, dict)]
        raw_result = lora_payload.get("raw_result")
        if tool_execution is None and isinstance(raw_result, dict) and isinstance(raw_result.get("tool_execution"), dict):
            tool_execution = dict(raw_result.get("tool_execution") or {})
        if not tool_diagnostics and isinstance(raw_result, dict) and isinstance(raw_result.get("tool_diagnostics"), list):
            tool_diagnostics = [dict(item) for item in raw_result.get("tool_diagnostics", []) if isinstance(item, dict)]

    lane_info = classify_runtime_lane(
        response=r,
        safe_fallback=safe,
        node_fallback=node_fb,
        mock_response=mock,
        last_runtime_mode=last_runtime_mode,
        last_runtime_reason=last_runtime_reason,
        node_cognitive_hint=node_cognitive_hint,
        node_outcome=node_outcome,
        direct_memory_hit=direct_memory_hit,
        strategy_dispatch_applied=bool((lora_payload or {}).get("strategy_dispatch_applied", False)),
    )
    semantic_lane = str(lane_info.get("semantic_lane") or "")
    transport_status = str(lane_info.get("transport_status") or "")
    hint_lane = str(lane_info.get("node_hint_lane") or "")
    node_matcher = semantic_lane == LANE_MATCHER_SHORTCUT
    execution_summary = str(
        (lora_payload or {}).get("execution_trace_summary", "")
        or (
            ((lora_payload or {}).get("trace") or {}).get("execution_trace_summary", "")
            if isinstance((lora_payload or {}).get("trace"), dict)
            else ""
        )
    )
    executor_used = str((lora_payload or {}).get("executor_used", "") or "")
    trace_payload = (lora_payload or {}).get("trace") if isinstance((lora_payload or {}).get("trace"), dict) else {}
    explicit_execution_lane = str(
        (lora_payload or {}).get("execution_runtime_lane", "")
        or trace_payload.get("execution_runtime_lane", "")
        or ""
    ).strip()
    explicit_compatibility_execution_active = None
    if isinstance(lora_payload, dict) and "compatibility_execution_active" in lora_payload:
        explicit_compatibility_execution_active = bool(lora_payload.get("compatibility_execution_active"))
    elif isinstance(trace_payload, dict) and "compatibility_execution_active" in trace_payload:
        explicit_compatibility_execution_active = bool(trace_payload.get("compatibility_execution_active"))
    actions_executed = bool(
        (node_outcome or {}).get("actions_executed", False)
        or (node_outcome or {}).get("has_actions", False)
        or (lora_payload or {}).get("true_action_execution_active", False)
        or trace_payload.get("true_action_execution_active", False)
    )
    execution_lane_info = classify_execution_runtime_lane(
        semantic_lane=semantic_lane,
        direct_memory_hit=direct_memory_hit,
        strategy_dispatch_applied=bool((lora_payload or {}).get("strategy_dispatch_applied", False)),
        executor_used=executor_used,
        execution_trace_summary=execution_summary,
        explicit_execution_runtime_lane=explicit_execution_lane,
        explicit_compatibility_execution_active=explicit_compatibility_execution_active,
        actions_executed=actions_executed,
    )
    execution_runtime_lane = str(execution_lane_info.get("execution_runtime_lane") or semantic_lane or "")
    compatibility_execution_active = bool(execution_lane_info.get("compatibility_execution_active", False))
    execution_path_used = str(
        (lora_payload or {}).get("execution_path_used", "")
        or trace_payload.get("execution_path_used", "")
        or ""
    ).strip()
    if not execution_path_used and semantic_lane in {
        LANE_MATCHER_SHORTCUT,
        LANE_LOCAL_DIRECT_RESPONSE,
        LANE_BRIDGE_EXECUTION_REQUEST,
        LANE_TRUE_ACTION_EXECUTION,
    }:
        execution_path_used = "node_execution"
    explicit_fallback_triggered = None
    if isinstance(lora_payload, dict) and "fallback_triggered" in lora_payload:
        explicit_fallback_triggered = bool(lora_payload.get("fallback_triggered"))
    elif isinstance(trace_payload, dict) and "fallback_triggered" in trace_payload:
        explicit_fallback_triggered = bool(trace_payload.get("fallback_triggered"))
    runtime_reason = str(lane_info.get("reason_code") or last_runtime_reason or "").strip()
    node_failure_reasons = {
        "timeout",
        "subprocess_exception",
        "empty_stdout",
        "empty_node_response",
        "node_not_found",
        "runner_not_found",
        "cwd_not_found",
        "module_resolution_error",
        "node_subprocess_failed",
        "invalid_json",
        "invalid_node_payload",
        "invalid_execution_request",
        "node_bridge_empty_stdout",
        "node_bridge_invalid_json",
        "node_bridge_nonzero_exit",
        "node_bridge_timeout",
        "node_empty_response",
        "NODE_BRIDGE_EMPTY_STDOUT",
        "NODE_BRIDGE_INVALID_JSON",
        "NODE_BRIDGE_NONZERO_EXIT",
        "NODE_BRIDGE_TIMEOUT",
        "NODE_EMPTY_RESPONSE",
    }
    node_failure = semantic_lane == LANE_SAFE_DEGRADED_FALLBACK and runtime_reason in node_failure_reasons
    fallback_triggered = (
        bool(explicit_fallback_triggered)
        if explicit_fallback_triggered is not None
        else bool(
            semantic_lane == LANE_SAFE_DEGRADED_FALLBACK
            or str(last_runtime_mode or "").strip() == "fallback"
            or r in {safe, node_fb, mock}
        )
    )

    learning_path = ""
    phase10_learning_record = {}
    learning_record_created = False
    phase10_decision_correct = None
    phase10_decision_issue = ""
    phase10_improvement_signals: list[dict[str, Any]] = []
    if isinstance(learning_record, dict):
        assess = learning_record.get("assessment")
        if isinstance(assess, dict):
            learning_path = str(assess.get("execution_path") or "")
        if isinstance(learning_record.get("phase10_learning_record"), dict):
            phase10_learning_record = dict(learning_record.get("phase10_learning_record") or {})
        learning_record_created = bool(learning_record.get("learning_record_created", False))
        phase10_decision_correct = learning_record.get("decision_correct")
        phase10_decision_issue = str(learning_record.get("decision_issue", "") or "")
        if isinstance(learning_record.get("phase10_improvement_signals"), list):
            phase10_improvement_signals = [
                dict(item) for item in learning_record.get("phase10_improvement_signals", []) if isinstance(item, dict)
            ]

    if provider_failed:
        runtime_reason = failure_class or runtime_reason or "provider_failure"
        runtime_mode = RUNTIME_MODE_PROVIDER_FAILURE
        source = SOURCE_NODE if execution_path_used == "node_execution" else SOURCE_PYTHON
        failures.append(f"provider_failure:{failure_class or provider_actual or 'unknown'}")
    elif node_failure:
        runtime_mode = RUNTIME_MODE_NODE_FB
        source = SOURCE_FALLBACK
        failures.append(f"node_failure:{runtime_reason or 'unknown'}")
    elif fallback_triggered:
        runtime_mode = RUNTIME_MODE_SAFE_FB
        source = SOURCE_FALLBACK
        failures.append(f"fallback_triggered:{runtime_reason or 'unknown'}")
    elif semantic_lane == LANE_MATCHER_SHORTCUT:
        runtime_mode = RUNTIME_MODE_MATCHER
        source = SOURCE_MATCHER
        failures.append("matcher_shortcut_bypassed_llm_grounding")
    elif execution_runtime_lane == "local_tool_execution" or hint_lane == "node_local_tool_run":
        runtime_mode = RUNTIME_MODE_LOCAL_TOOL_SUCCESS
        source = SOURCE_NODE
    elif semantic_lane == LANE_LOCAL_DIRECT_RESPONSE:
        runtime_mode = RUNTIME_MODE_LOCAL_DIRECT
        source = SOURCE_NODE
    elif semantic_lane == LANE_TRUE_ACTION_EXECUTION:
        runtime_mode = RUNTIME_MODE_NODE_OK
        source = SOURCE_NODE
    elif semantic_lane == LANE_COMPATIBILITY_EXECUTION or compatibility_execution_active:
        runtime_mode = RUNTIME_MODE_COMPAT
        source = SOURCE_PYTHON if direct_memory_hit else SOURCE_NODE
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

    node_graph = semantic_lane in {LANE_BRIDGE_EXECUTION_REQUEST, LANE_TRUE_ACTION_EXECUTION}
    node_soft = semantic_lane in {LANE_MATCHER_SHORTCUT, LANE_LOCAL_DIRECT_RESPONSE}
    tools_or_sim = semantic_lane == LANE_TRUE_ACTION_EXECUTION

    chain_parts = {
        "strategy_generation": strat_ok,
        "reasoning_trace_oil": reason_ok,
        "planning_execution_ready": plan_ok,
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

    if runtime_mode in (RUNTIME_MODE_NODE_FB, RUNTIME_MODE_SAFE_FB, RUNTIME_MODE_PROVIDER_FAILURE):
        cognitive_chain = CHAIN_BROKEN

    if compatibility_execution_active and runtime_mode == RUNTIME_MODE_NODE_OK:
        runtime_mode = RUNTIME_MODE_COMPAT

    # Performance heuristics.
    if direct_memory_hit:
        perf_notes.append("swarm_node_skipped_due_to_direct_memory_hit")
    elif learning_path == "swarm" and reason_ok and strat_ok:
        perf_notes.append("python_reasoning_strategy_then_node_planner_likely_redundant_work")
    if compatibility_execution_active:
        perf_notes.append("compatibility_execution_active_degraded_but_supported")

    if duration_ms > 45_000:
        perf_notes.append("high_latency_risk_subprocess_and_dual_runtime")

    # FULL only if chain complete, non-matcher, non-fallback, live mode, swarm path used tools graph.
    if (
        runtime_mode == RUNTIME_MODE_NODE_OK
        and cognitive_chain == CHAIN_COMPLETE
        and not node_matcher
        and not direct_memory_hit
        and tools_or_sim
        and execution_path_used == "node_execution"
        and not compatibility_execution_active
    ):
        runtime_mode = RUNTIME_MODE_FULL

    # Final verdict (conservative).
    if runtime_mode in (RUNTIME_MODE_NODE_FB, RUNTIME_MODE_SAFE_FB, RUNTIME_MODE_PROVIDER_FAILURE):
        verdict = VERDICT_DEGRADED
    elif runtime_mode == RUNTIME_MODE_MATCHER or validation in {"invalid", "fallback"} or strat_deg:
        verdict = VERDICT_HYBRID
    elif runtime_mode == RUNTIME_MODE_FULL and cognitive_chain == CHAIN_COMPLETE:
        verdict = VERDICT_TRUE
    else:
        verdict = VERDICT_HYBRID

    if compatibility_execution_active and verdict == VERDICT_TRUE:
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
            "ambiguity_detected": bool(lora_payload.get("ambiguity_detected", False)),
            "ambiguity_score": float(lora_payload.get("ambiguity_score", 0.0) or 0.0),
            "ranking_applied": bool(lora_payload.get("ranking_candidates_count", 0)),
            "ranking_candidates_count": int(lora_payload.get("ranking_candidates_count", 0) or 0),
            "ranked_strategy": str(lora_payload.get("selected_strategy", "") or ""),
            "ranked_confidence": float(lora_payload.get("ranked_confidence", 0.0) or 0.0),
            "ranking_source": str(lora_payload.get("ranking_source", lora_payload.get("decision_source", "rule")) or "rule"),
            "deterministic_strategy": str(lora_payload.get("deterministic_strategy", "") or ""),
            "decision_final_source": str(lora_payload.get("decision_source", "rule") or "rule"),
            "strategy_dispatch_applied": bool(lora_payload.get("strategy_dispatch_applied", False)),
            "executor_used": str(lora_payload.get("executor_used", "") or ""),
            "strategy_execution_status": str(lora_payload.get("status", "") or lora_payload.get("strategy_execution_status", "") or ""),
            "strategy_execution_fallback": bool(lora_payload.get("fallback_applied", False) or lora_payload.get("strategy_execution_fallback", False)),
            "manifest_driven_execution": bool(lora_payload.get("manifest_driven_execution", False)),
            "response_synthesis_mode": str(lora_payload.get("response_synthesis_mode", "") or ""),
            "governance_downgrade_applied": bool(lora_payload.get("governance_downgrade_applied", False)),
            "decision_task_type": str(lora_payload.get("decision_task_type", "") or ""),
            "decision_reasoning": str(lora_payload.get("decision_reasoning", "") or ""),
            "decision_reason_codes": list(lora_payload.get("decision_reason_codes", []) or []),
            "decision_requires_tools": bool(lora_payload.get("decision_requires_tools", False)),
            "decision_requires_node_runtime": bool(lora_payload.get("decision_requires_node_runtime", False)),
            "decision_must_execute": bool(lora_payload.get("decision_must_execute", False)),
            "decision_suggested_tools": list(lora_payload.get("decision_suggested_tools", []) or []),
            "decision_preferred_capability_path": str(
                lora_payload.get("decision_preferred_capability_path", "") or ""
            ),
            "execution_trace_summary": str(
                (lora_payload.get("trace") or {}).get("execution_trace_summary", "")
                if isinstance(lora_payload.get("trace"), dict)
                else lora_payload.get("execution_trace_summary", "")
            ),
        }

    node_execution_successful = bool(
        transport_status == TRANSPORT_SUCCESS
        and execution_path_used == "node_execution"
        and runtime_mode in {RUNTIME_MODE_NODE_OK, RUNTIME_MODE_FULL, RUNTIME_MODE_LOCAL_TOOL_SUCCESS}
    )

    tool_status = _truth_tool_status(tool_execution)
    tool_invoked = tool_status not in {"not_invoked"}
    tool_executed = tool_status == "executed"
    tool_blocked = tool_status == "blocked"
    matcher_used = semantic_lane == LANE_MATCHER_SHORTCUT
    provider_is_llm = bool(provider_actual and provider_actual not in {"local-heuristic", "embedded", "native-heuristic"})
    llm_provider_attempted = bool(provider_is_llm and not matcher_used)
    llm_provider_succeeded = bool(llm_provider_attempted and not provider_failed and not failure_class)
    node_invoked = bool(execution_path_used == "node_execution" or isinstance(node_outcome, dict) or node_cognitive_hint)
    node_exit_code = None
    if isinstance(node_outcome, dict):
        raw_exit_code = node_outcome.get("exit_code", node_outcome.get("returncode"))
        try:
            node_exit_code = int(raw_exit_code) if raw_exit_code is not None else None
        except (TypeError, ValueError):
            node_exit_code = None
    intent = ""
    intent_source = "rule_based"
    classifier_version = "regex_v1"
    if isinstance(node_outcome, dict):
        intent = str(node_outcome.get("intent") or "").strip()
        intent_source = str(node_outcome.get("intent_source") or intent_source).strip() or "rule_based"
        classifier_version = str(node_outcome.get("classifier_version") or classifier_version).strip() or "regex_v1"
        raw_truth = node_outcome.get("runtime_truth")
        if isinstance(raw_truth, dict):
            intent = str(raw_truth.get("intent") or intent).strip()
            intent_source = str(raw_truth.get("intent_source") or intent_source).strip() or "rule_based"
            classifier_version = str(raw_truth.get("classifier_version") or classifier_version).strip() or "regex_v1"
    if isinstance(lora_payload, dict):
        raw_truth = lora_payload.get("runtime_truth")
        if isinstance(raw_truth, dict):
            intent = str(raw_truth.get("intent") or intent).strip()
            intent_source = str(raw_truth.get("intent_source") or intent_source).strip() or "rule_based"
            classifier_version = str(raw_truth.get("classifier_version") or classifier_version).strip() or "regex_v1"

    if node_failure:
        truth_runtime_mode = TRUTH_MODE_NODE_FALLBACK
    elif fallback_triggered:
        truth_runtime_mode = TRUTH_MODE_SAFE_FALLBACK
    elif provider_failed or no_provider_available:
        truth_runtime_mode = TRUTH_MODE_PROVIDER_UNAVAILABLE
        llm_provider_succeeded = False
    elif tool_blocked:
        truth_runtime_mode = TRUTH_MODE_TOOL_BLOCKED
    elif tool_executed:
        truth_runtime_mode = TRUTH_MODE_TOOL_EXECUTED
    elif matcher_used:
        truth_runtime_mode = TRUTH_MODE_MATCHER_SHORTCUT
        llm_provider_attempted = False
        llm_provider_succeeded = False
        tool_invoked = False
    elif direct_memory_hit:
        truth_runtime_mode = TRUTH_MODE_MEMORY_ONLY_RESPONSE
        llm_provider_succeeded = False
    elif semantic_lane == LANE_LOCAL_DIRECT_RESPONSE:
        truth_runtime_mode = TRUTH_MODE_RULE_BASED_INTENT
    elif runtime_mode == RUNTIME_MODE_FULL:
        truth_runtime_mode = TRUTH_MODE_FULL_COGNITIVE_RUNTIME
    elif semantic_lane == LANE_BRIDGE_EXECUTION_REQUEST:
        truth_runtime_mode = TRUTH_MODE_PARTIAL_COGNITIVE
    else:
        truth_runtime_mode = TRUTH_MODE_PARTIAL_COGNITIVE

    if fallback_triggered and truth_runtime_mode == TRUTH_MODE_FULL_COGNITIVE_RUNTIME:
        truth_runtime_mode = TRUTH_MODE_SAFE_FALLBACK

    truth_error_code = _truth_error_code(truth_runtime_mode)
    truth_public_error = build_public_error(truth_error_code) if truth_error_code else {}
    runtime_truth = {
        "runtime_mode": truth_runtime_mode,
        "runtime_reason": runtime_reason,
        "intent": intent,
        "intent_source": intent_source,
        "classifier_version": classifier_version,
        "matcher_used": matcher_used,
        "llm_provider_attempted": llm_provider_attempted,
        "llm_provider_succeeded": llm_provider_succeeded,
        "tool_invoked": tool_invoked,
        "tool_executed": tool_executed,
        "tool_status": tool_status,
        "fallback_triggered": fallback_triggered,
        "node_invoked": node_invoked,
        "node_exit_code": node_exit_code,
        "error_public_code": truth_public_error.get("error_public_code", ""),
        "error_public_message": truth_public_error.get("error_public_message", ""),
        "severity": truth_public_error.get("severity", "info"),
        "retryable": bool(truth_public_error.get("retryable", False)),
        "internal_error_redacted": bool(truth_public_error.get("internal_error_redacted", True)),
        "public_summary": _truth_public_summary(truth_runtime_mode),
    }

    return {
        "runtime_mode": runtime_mode,
        "runtime_reason": runtime_reason,
        "runtime_truth": runtime_truth,
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
            "runtime_reason": runtime_reason,
            "runtime_truth": runtime_truth,
            "intent": intent,
            "intent_source": intent_source,
            "classifier_version": classifier_version,
            "matcher_used": matcher_used,
            "llm_provider_attempted": llm_provider_attempted,
            "llm_provider_succeeded": llm_provider_succeeded,
            "tool_invoked": tool_invoked,
            "tool_executed": tool_executed,
            "tool_status": tool_status,
            "node_invoked": node_invoked,
            "node_exit_code": node_exit_code,
            "public_summary": runtime_truth["public_summary"],
            "last_runtime_mode": str(last_runtime_mode or ""),
            "last_runtime_reason": str(last_runtime_reason or ""),
            "semantic_runtime_lane": semantic_lane or LANE_COMPATIBILITY_EXECUTION,
            "execution_runtime_lane": execution_runtime_lane or LANE_COMPATIBILITY_EXECUTION,
            "compatibility_execution_active": compatibility_execution_active,
            "execution_path_used": execution_path_used,
            "fallback_triggered": fallback_triggered,
            "transport_status": transport_status or TRANSPORT_SUCCESS,
            "provider_actual": provider_actual,
            "provider_failed": provider_failed,
            "failure_class": failure_class,
            "failure_reason": failure_reason or None,
            "provider_diagnostics": provider_diagnostics or None,
            "provider_fallback_occurred": provider_fallback_occurred,
            "no_provider_available": no_provider_available,
            "tool_execution": tool_execution,
            "tool_diagnostics": tool_diagnostics or None,
            "tool_requested": bool(tool_execution.get("tool_requested")) if isinstance(tool_execution, dict) else False,
            "tool_selected": tool_execution.get("tool_selected") if isinstance(tool_execution, dict) else None,
            "tool_available": bool(tool_execution.get("tool_available")) if isinstance(tool_execution, dict) else False,
            "tool_attempted": bool(tool_execution.get("tool_attempted")) if isinstance(tool_execution, dict) else False,
            "tool_succeeded": bool(tool_execution.get("tool_succeeded")) if isinstance(tool_execution, dict) else False,
            "tool_failed": bool(tool_execution.get("tool_failed")) if isinstance(tool_execution, dict) else False,
            "tool_denied": bool(tool_execution.get("tool_denied")) if isinstance(tool_execution, dict) else False,
            "tool_failure_class": tool_execution.get("tool_failure_class") if isinstance(tool_execution, dict) else None,
            "tool_failure_reason": tool_execution.get("tool_failure_reason") if isinstance(tool_execution, dict) else None,
            "tool_latency_ms": tool_execution.get("tool_latency_ms") if isinstance(tool_execution, dict) else None,
            "execution_provenance": execution_provenance or None,
            "node_execution_successful": node_execution_successful,
            "coarse_runtime_mode": (
                RUNTIME_MODE_NODE_FB
                if node_failure
                else RUNTIME_MODE_SAFE_FB
                if fallback_triggered
                else RUNTIME_MODE_MATCHER
                if semantic_lane == LANE_MATCHER_SHORTCUT
                else RUNTIME_MODE_LOCAL_DIRECT
                if semantic_lane == LANE_LOCAL_DIRECT_RESPONSE
                else RUNTIME_MODE_LOCAL_TOOL_SUCCESS
                if execution_runtime_lane == "local_tool_execution" or hint_lane == "node_local_tool_run"
                else RUNTIME_MODE_NODE_OK
                if semantic_lane == LANE_TRUE_ACTION_EXECUTION
                else RUNTIME_MODE_COMPAT
                if compatibility_execution_active
                else RUNTIME_MODE_PARTIAL
            ),
            "runtime_mode_definitions": RUNTIME_MODE_DEFINITIONS,
            "reasoning_validation": validation or "unknown",
            "direct_memory_hit": bool(direct_memory_hit),
            "learning_execution_path": learning_path or "unknown",
            "node_cognitive_hint": node_cognitive_hint if isinstance(node_cognitive_hint, dict) else None,
            "node_outcome": node_outcome if isinstance(node_outcome, dict) else None,
            "duration_ms": int(duration_ms),
            "learning_record_created": learning_record_created,
            "decision_correct": phase10_decision_correct,
            "decision_issue": phase10_decision_issue or None,
            "phase10_learning_record": phase10_learning_record or None,
            "phase10_improvement_signals": phase10_improvement_signals or None,
            **lora_signals,
        },
    }
