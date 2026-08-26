"""Primary execution lane strategies extracted from BrainOrchestrator.

Owns lane selection and the primary execution paths: node subprocess,
local tool execution, planner path, compatibility-with-synthesis, strategy
compatible dispatch, and true-action routing decisions.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
from pathlib import Path
from typing import Any

from brain.env import read_env
from brain.runtime.control.run_identity import coerce_runtime_run_id
from brain.runtime.engineering_tools import supports_engineering_tool
from brain.runtime.observability.runtime_lane_classifier import (
    LANE_BRIDGE_EXECUTION_REQUEST,
    LANE_COMPATIBILITY_EXECUTION,
    LANE_LOCAL_DIRECT_RESPONSE,
    LANE_SAFE_DEGRADED_FALLBACK,
    LANE_TRUE_ACTION_EXECUTION,
)
from brain.runtime.observability.tool_execution_diagnostics import summarize_tool_execution
from brain.runtime.serializers import budget_to_dict, retrieval_plan_to_dict
from config.provider_registry import get_available_providers

SAFE_FALLBACK_RESPONSE = "Nao consegui processar isso ainda, mas estou aprendendo."
NODE_FALLBACK_RESPONSE = (
    "Modo fallback ativo: o motor Node nao respondeu de forma utilizavel, "
    "entao mantive uma resposta degradada e segura."
)


class ExecutionLaneService:
    """Executes primary runtime lanes on behalf of BrainOrchestrator."""

    __slots__ = ("_orch",)

    def __init__(self, orchestrator: object) -> None:
        self._orch = orchestrator

    def select_primary_execution_type(
        self,
        *,
        routing_decision: Any,
        upgrade_artifacts: dict[str, Any],
        selected_tools: list[str] | None,
        direct_response: str,
    ) -> str:
        o = self._orch
        if str(direct_response or "").strip():
            return "DIRECT_RESPONSE"
        manifest_payload = dict(upgrade_artifacts.get("manifest") or {})
        step_plan = list(manifest_payload.get("step_plan", []) or [])
        step_kinds = {
            str(item.get("kind", "") or "").strip().lower()
            for item in step_plan
            if isinstance(item, dict)
        }
        oil_intent = str((upgrade_artifacts.get("oil_summary") or {}).get("intent", "") or "").strip().lower()
        output_mode = str(manifest_payload.get("output_mode", "") or "").strip().lower()
        selected_strategy = str(getattr(routing_decision, "strategy", "") or "").strip().upper()
        deterministic_tool_first = bool(getattr(routing_decision, "must_execute", False)) and (
            "deterministic_tool_first"
            in list(getattr(routing_decision, "decision_reason_codes", []) or [])
        )
        if (
            deterministic_tool_first
            and selected_tools
            and all(supports_engineering_tool(str(tool)) for tool in selected_tools)
        ):
            return "LOCAL_TOOL_EXECUTION"
        if "delegate" in step_kinds or bool(getattr(routing_decision, "requires_node_runtime", False)):
            return "NODE_EXECUTION"
        if selected_strategy == "MULTI_STEP_REASONING":
            return "PLANNER_EXECUTION"
        if selected_tools and "tool" in step_kinds and all(supports_engineering_tool(str(tool)) for tool in selected_tools):
            return "LOCAL_TOOL_EXECUTION"
        if len(step_plan) > 2 or str(getattr(routing_decision, "execution_strategy", "") or "").strip().lower() in {
            "multi_step_reasoning",
            "planning",
            "planner_execution",
        }:
            return "PLANNER_EXECUTION"
        if selected_strategy == "TOOL_ASSISTED" and selected_tools and "tool" in step_kinds:
            return "LOCAL_TOOL_EXECUTION" if all(supports_engineering_tool(str(tool)) for tool in selected_tools) else "NODE_EXECUTION"
        if "tool" in step_kinds:
            return "LOCAL_TOOL_EXECUTION"
        if selected_strategy == "DIRECT_RESPONSE":
            return "COMPATIBILITY_EXECUTION"
        if oil_intent in {"execute", "plan"} or output_mode == "structured":
            return "NODE_EXECUTION"
        return "NODE_EXECUTION"


    def build_primary_node_result(
        self,
        *,
        response_text: str,
        predicted_intent: str,
    ) -> dict[str, Any]:
        o = self._orch
        node_env = getattr(o, "_last_node_result_envelope", None)
        node_outcome = getattr(o, "_last_node_outcome", None)
        primary_result: dict[str, Any] = {
            "response": response_text,
            "intent": predicted_intent,
            "delegates": [],
            "agent_trace": [],
            "memory_signal": {},
            "metadata": {"execution_path": "primary_node_execution"},
        }
        if isinstance(node_env, dict):
            metadata = node_env.get("metadata")
            if isinstance(metadata, dict):
                primary_result["metadata"] = {
                    **dict(primary_result.get("metadata") or {}),
                    **metadata,
                }
            execution_provenance = metadata.get("execution_provenance") if isinstance(metadata, dict) else None
            if isinstance(execution_provenance, dict):
                primary_result["execution_provenance"] = execution_provenance
            cognitive_runtime_hint = node_env.get("cognitive_runtime_hint")
            if isinstance(cognitive_runtime_hint, dict):
                primary_result["cognitive_runtime_hint"] = cognitive_runtime_hint
        if isinstance(node_outcome, dict):
            semantic_lane = str(node_outcome.get("semantic_lane", "") or "").strip()
            execution_lane = str(node_outcome.get("execution_runtime_lane", "") or "").strip()
            if semantic_lane:
                primary_result["semantic_runtime_lane"] = semantic_lane
                primary_result["execution_runtime_lane"] = execution_lane or semantic_lane
            if bool(node_outcome.get("actions_executed")):
                primary_result["true_action_execution_active"] = True
                primary_result["compatibility_execution_active"] = False
        if isinstance(getattr(o, "_last_runtime_step_results", None), list) and o._last_runtime_step_results:
            primary_result["step_results"] = [dict(item) for item in o._last_runtime_step_results if isinstance(item, dict)]
        if isinstance(getattr(o, "_last_tool_execution", None), dict):
            primary_result["tool_execution"] = dict(o._last_tool_execution)
        if isinstance(getattr(o, "_last_tool_diagnostics", None), list):
            primary_result["tool_diagnostics"] = [dict(item) for item in o._last_tool_diagnostics if isinstance(item, dict)]
        return primary_result


    def execute_primary_node_path(
        self,
        *,
        session_id: str,
        runtime_message: str,
        predicted_intent: str,
        memory_store: dict[str, Any],
        available_capabilities: list[dict[str, str]],
        suggested_tools: list[str] | None = None,
        extra_session: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        o = self._orch
        o._append_runtime_event(
            event_type="runtime.execution.primary_path",
            session_id=session_id,
            task_id="",
            run_id="",
            payload={"strategy_selected": "primary_node_execution", "fallback_triggered": False},
        )
        response_text = str(
            o._call_node_query_engine(
                message=runtime_message,
                memory_store=memory_store,
                available_capabilities=available_capabilities,
                session_id=session_id,
                extra_session=extra_session or {},
            )
            or ""
        ).strip()
        node_outcome = getattr(o, "_last_node_outcome", None)
        semantic_lane = str((node_outcome or {}).get("semantic_lane", "") or "").strip()
        
        # Synthesize only when Node failed to produce a usable response. A successful
        # bridge response without actions is runtime truth, not permission to execute.
        if (
            not response_text
            or semantic_lane == LANE_SAFE_DEGRADED_FALLBACK
        ) and o._should_synthesize_execution_request(runtime_message, available_capabilities, suggested_tools):
            synth_request = o._synthesize_execution_request(
                message=runtime_message,
                session_id=session_id,
                available_capabilities=available_capabilities,
                suggested_tools=suggested_tools,
                memory_store=memory_store,
            )
            # Execute via true action path directly (bypasses StrategyDispatcher loop)
            result_text = o._execute_true_action_path(
                execution_request=synth_request,
                session_id=session_id,
                message=runtime_message,
                memory_store=memory_store,
                fallback_response_text=response_text or NODE_FALLBACK_RESPONSE,
            )
            # Build result from true action execution
            primary_result = self.build_primary_node_result(
                response_text=result_text,
                predicted_intent=predicted_intent,
            )
            o._append_runtime_event(
                event_type="runtime.execution.primary_path",
                session_id=session_id,
                task_id="",
                run_id="",
                payload={
                    "strategy_selected": "primary_node_execution_synthesized",
                    "execution_path_used": "synthesized_true_action",
                    "fallback_triggered": False,
                },
            )
            return primary_result
        
        if not response_text or semantic_lane == LANE_SAFE_DEGRADED_FALLBACK:
            o._append_runtime_event(
                event_type="runtime.execution.primary_path",
                session_id=session_id,
                task_id="",
                run_id="",
                payload={
                    "strategy_selected": "primary_node_execution",
                    "node_call_result": str(o.last_runtime_reason or "empty_node_response"),
                    "fallback_triggered": True,
                },
            )
            return {}
        primary_result = self.build_primary_node_result(
            response_text=response_text,
            predicted_intent=predicted_intent,
        )
        o._append_runtime_event(
            event_type="runtime.execution.primary_path",
            session_id=session_id,
            task_id="",
            run_id="",
            payload={
                "strategy_selected": "primary_node_execution",
                "execution_path_used": "node_execution",
                "node_call_result": semantic_lane or str(o.last_runtime_reason or "direct_node_response"),
                "fallback_triggered": False,
            },
        )
        return primary_result


    def get_primary_path_success_rate(
        self,
    ) -> dict[str, Any]:
        o = self._orch
        m = dict(o._primary_path_metrics)
        attempts = m.get("attempts", 0)
        successes = m.get("successes", 0)
        fallbacks = m.get("fallbacks", 0)
        m["fallback_rate_pct"] = round((fallbacks / attempts * 100) if attempts > 0 else 0.0, 1)
        m["success_rate_pct"] = round((successes / attempts * 100) if attempts > 0 else 0.0, 1)
        m["total_attempts"] = attempts
        return m


    def get_runtime_metrics(
        self,
    ) -> dict[str, Any]:
        o = self._orch
        return {
            **o.metrics_collector.snapshot(),
            "primary_path": self.get_primary_path_success_rate(),
            "node_circuit_breaker": o._node_circuit.snapshot(),
        }


    def extract_local_tool_target(
        self,
        message: str,
    ) -> str:
        o = self._orch
        match = re.search(r"([A-Za-z0-9_./\\\\-]+\.(?:json|md|py|js|ts|tsx|rs|toml|yaml|yml))", str(message or ""))
        if not match:
            return ""
        return str(match.group(1) or "").strip()


    def execute_primary_local_tool_path(
        self,
        *,
        session_id: str,
        runtime_message: str,
        predicted_intent: str,
        selected_tools: list[str],
    ) -> dict[str, Any]:
        o = self._orch
        tool_name = str(selected_tools[0] if selected_tools else "").strip()
        if not tool_name:
            return {}
        target_path = self.extract_local_tool_target(runtime_message)
        if tool_name in {"read_file", "filesystem_read", "glob_search"} and not target_path:
            return {}
        tool_arguments: dict[str, Any] = {}
        if tool_name in {"read_file", "filesystem_read"}:
            tool_arguments["path"] = target_path
        elif tool_name == "glob_search":
            tool_arguments["pattern"] = Path(target_path).name or target_path
            tool_arguments["path"] = "."
        step_results = o._execute_runtime_actions(
            session_id=session_id,
            message=runtime_message,
            actions=[
                {
                    "step_id": "primary-local-tool",
                    "selected_tool": tool_name,
                    "tool_arguments": tool_arguments,
                    "description": f"Primary local tool execution via {tool_name}",
                }
            ],
            task_id=f"task-{session_id}",
            run_id=coerce_runtime_run_id(run_id="", session_id=session_id),
            provider="local-runtime",
            intent=predicted_intent,
            delegation={},
            critic_review={},
            plan_kind="linear",
            plan_graph=None,
            semantic_retrieval=[],
            plan_hierarchy=None,
            learning_guidance=[],
            policy_summary=[],
            branch_plan=None,
            simulation_summary=None,
            cooperative_plan=None,
            strategy_suggestions=[],
            execution_tree=None,
            negotiation_summary=None,
            strategy_optimization=None,
            repository_analysis=None,
            repo_impact_analysis=None,
            verification_plan=None,
            verification_selection=None,
            milestone_plan=None,
            engineering_review=None,
            engineering_workflow=None,
            operator_control_enabled=True,
        )
        response_text = str(o._synthesize_runtime_response(step_results, "") or "").strip()
        if not response_text:
            return {}
        o.last_runtime_reason = "local_tool_execution"
        tool_execution, tool_diagnostics = summarize_tool_execution(
            step_results=step_results,
            selected_tools=selected_tools,
        )
        return {
            "response": response_text,
            "intent": predicted_intent,
            "delegates": [],
            "agent_trace": [],
            "memory_signal": {},
            "step_results": step_results,
            "metadata": {"execution_path": "primary_local_tool_execution", "selected_tool": tool_name},
            "semantic_runtime_lane": LANE_LOCAL_DIRECT_RESPONSE,
            "execution_runtime_lane": "local_tool_execution",
            "compatibility_execution_active": False,
            "tool_execution": tool_execution,
            "tool_diagnostics": tool_diagnostics,
        }


    def execute_primary_planner_path(
        self,
        *,
        session_id: str,
        runtime_message: str,
        predicted_intent: str,
        memory_store: dict[str, Any],
        available_capabilities: list[dict[str, str]],
    ) -> dict[str, Any]:
        o = self._orch
        primary_result = self.execute_primary_node_path(
            session_id=session_id,
            runtime_message=runtime_message,
            predicted_intent=predicted_intent,
            memory_store=memory_store,
            available_capabilities=available_capabilities,
            extra_session={},
        )
        if primary_result:
            metadata = dict(primary_result.get("metadata") or {})
            metadata["execution_path"] = "primary_planner_execution"
            primary_result["metadata"] = metadata
        return primary_result


    def execute_compat_with_synthesis(
        self,
        *,
        session_id: str,
        runtime_message: str,
        predicted_intent: str,
        direct_response: str,
        strategy_payload: dict[str, Any] | None,
        planning_payload: dict[str, Any],
        reasoning_handoff: dict[str, Any],
        reasoning_payload: dict[str, Any],
        memory_context: dict[str, Any],
        memory_context_payload: dict[str, Any],
        control_execution_summary: dict[str, Any],
        context_budget: Any,
        retrieval_plan: Any,
        phase39_tuning: dict[str, Any],
        budgeted_history: list[dict[str, Any]],
        summary: str,
        available_capabilities: list[dict[str, str]],
        suggested_tools: list[str] | None,
        memory_store: dict[str, Any],
        coordination_payload: dict[str, Any],
    ) -> dict[str, Any]:
        o = self._orch
        """Execute compatibility path with synthesis for tool-capable prompts when Node fails."""
        node_outcome = getattr(o, "_last_node_outcome", None)
        if (
            isinstance(node_outcome, dict)
            and str(node_outcome.get("semantic_lane", "") or "").strip() == LANE_BRIDGE_EXECUTION_REQUEST
            and not bool(node_outcome.get("has_actions", False))
        ):
            node_envelope = getattr(o, "_last_node_result_envelope", None)
            bridge_response = str(direct_response or "").strip()
            if not bridge_response and isinstance(node_envelope, dict):
                bridge_response = str(node_envelope.get("response", "") or "").strip()
            bridge_response = bridge_response or str(node_outcome.get("response_text", "") or "").strip()
            return self.build_primary_node_result(
                response_text=bridge_response,
                predicted_intent=predicted_intent,
            )

        # Check if we should synthesize execution_request for tool-capable prompts
        if o._should_synthesize_execution_request(runtime_message, available_capabilities, suggested_tools):
            synth_request = o._synthesize_execution_request(
                message=runtime_message,
                session_id=session_id,
                available_capabilities=available_capabilities,
                suggested_tools=suggested_tools,
                memory_store=memory_store,
            )
            # Execute via true action path (Rust bridge)
            result_text = o._execute_true_action_path(
                execution_request=synth_request,
                session_id=session_id,
                message=runtime_message,
                memory_store=memory_store,
                fallback_response_text=direct_response or NODE_FALLBACK_RESPONSE,
            )
            # Build result from true action execution
            compat_result = self.build_primary_node_result(
                response_text=result_text,
                predicted_intent=predicted_intent,
            )
            compat_result["metadata"] = compat_result.get("metadata", {})
            compat_result["metadata"]["execution_path"] = "compat_synthesized_true_action"
            return compat_result
        
        # Fall back to original compatibility path
        return self.execute_strategy_compatible_path(
            session_id=session_id,
            runtime_message=runtime_message,
            predicted_intent=predicted_intent,
            direct_response=direct_response,
            strategy_payload=strategy_payload,
            planning_payload=planning_payload,
            reasoning_handoff=reasoning_handoff,
            reasoning_payload=reasoning_payload,
            memory_context=memory_context,
            memory_context_payload=memory_context_payload,
            control_execution_summary=control_execution_summary,
            context_budget=context_budget,
            retrieval_plan=retrieval_plan,
            phase39_tuning=phase39_tuning,
            budgeted_history=budgeted_history,
            summary=summary,
            available_capabilities=available_capabilities,
            memory_store=memory_store,
            coordination_payload=coordination_payload,
        )


    def execute_strategy_compatible_path(
        self,
        *,
        session_id: str,
        runtime_message: str,
        predicted_intent: str,
        direct_response: str,
        strategy_payload: dict[str, Any] | None,
        planning_payload: dict[str, Any],
        reasoning_handoff: dict[str, Any],
        reasoning_payload: dict[str, Any],
        memory_context: dict[str, Any],
        memory_context_payload: dict[str, Any],
        control_execution_summary: dict[str, Any],
        context_budget: Any,
        retrieval_plan: Any,
        phase39_tuning: dict[str, Any],
        budgeted_history: list[dict[str, Any]],
        summary: str,
        available_capabilities: list[dict[str, str]],
        memory_store: dict[str, Any],
        coordination_payload: dict[str, Any],
    ) -> dict[str, Any]:
        o = self._orch
        swarm_result: dict[str, Any] = {
            "response": direct_response,
            "intent": predicted_intent,
            "delegates": [],
            "agent_trace": [],
            "memory_signal": {},
            "multi_agent_coordination": dict(coordination_payload),
        }
        if direct_response:
            skip_tid = "perf36-skip-" + hashlib.sha256(str(session_id or "").encode("utf-8")).hexdigest()[:10]
            performance_payload = {
                "trace": {
                    "trace_id": skip_tid,
                    "session_id": session_id,
                    "cache_hit": False,
                    "cache_key_fingerprint": "",
                    "compression_applied": ["skipped_direct_memory"],
                    "estimated_bytes_before": 0,
                    "estimated_bytes_after": 0,
                    "estimated_bytes_saved": 0,
                    "redundant_dict_copies_avoided": 0,
                    "degraded": False,
                    "error": "",
                },
                "stats": {"steps_applied": ["skipped_direct_memory"], "estimated_bytes_before": 0, "estimated_bytes_after": 0, "estimated_bytes_saved": 0},
            }
            o._append_runtime_event(
                event_type="runtime.performance_optimization.trace",
                session_id=session_id,
                task_id="",
                run_id="",
                payload=dict(performance_payload),
            )
            o._last_strategy_performance_payload = dict(performance_payload)
            return swarm_result

        recent_exp = o.experience_store.read_recent_for_session(session_id, limit=12)
        avail = get_available_providers()
        baseline = (avail[0] if avail else None) or None
        strat_mode = None
        if isinstance(strategy_payload, dict):
            ss = strategy_payload.get("selected_strategy")
            if isinstance(ss, dict):
                strat_mode = str(ss.get("mode", "") or "").strip() or None
        hint = o.policy_router.compute_hint(
            session_id=session_id,
            normalized_intent=str(predicted_intent or "unknown")[:256],
            baseline_provider=baseline,
            strategy_mode=strat_mode,
            recent_experience_rows=recent_exp,
        )
        o._last_phase41_policy_hint = hint.as_dict()
        if read_env("OMNI_PHASE41_POLICY_LOG", "1").lower() not in ("0", "false", "no", "off"):
            o._append_runtime_event(
                event_type="runtime.phase41.policy_shadow",
                session_id=session_id,
                task_id="",
                run_id="",
                payload={
                    "baseline_provider": hint.baseline_provider,
                    "recommended_provider": hint.recommended_provider,
                    "recommended_strategy": hint.recommended_strategy,
                    "confidence": hint.confidence,
                    "policy_reason_codes": hint.policy_reason_codes,
                    "shadow_only": hint.shadow_only,
                },
            )
        o._pending_policy_hint_json = o.policy_router.hint_to_env_json(hint)

        budget_dict = budget_to_dict(context_budget)
        retrieval_dict = retrieval_plan_to_dict(retrieval_plan)
        pcache = phase39_tuning.get("performance_max_cache_entries")
        cache_override = None
        try:
            if pcache is not None:
                cache_override = int(pcache)
        except (TypeError, ValueError):
            cache_override = None
        perf_result = o.performance_engine.optimize_swarm_boundary(
            session_id=session_id,
            message=runtime_message,
            budget_dict=budget_dict,
            retrieval_dict=retrieval_dict,
            structured_memory=memory_context["retrieved_context"],
            memory_intelligence=memory_context_payload,
            reasoning_handoff=reasoning_handoff,
            planning_payload=planning_payload,
            cache_max_override=cache_override,
        )
        swarm_context = dict(perf_result.slim_swarm_context)
        hb = coordination_payload.get("handoff_bundle")
        if isinstance(hb, dict):
            swarm_context["multi_agent_coordination"] = hb
        performance_payload = {
            "trace": perf_result.trace.as_dict(),
            "stats": perf_result.stats.as_dict(),
        }
        o._append_runtime_event(
            event_type="runtime.performance_optimization.trace",
            session_id=session_id,
            task_id="",
            run_id="",
            payload=dict(performance_payload),
        )
        o._last_strategy_performance_payload = dict(performance_payload)
        swarm_result = asyncio.run(
            o.swarm_coordinator.run(
                message=runtime_message,
                session_id=session_id,
                memory_store=memory_store,
                history=budgeted_history,
                summary=summary,
                capabilities=available_capabilities,
                context_session=swarm_context,
                executor=lambda payload: o._async_node_execution(
                    message=runtime_message,
                    memory_store=memory_store,
                    available_capabilities=available_capabilities,
                    session_id=session_id,
                    swarm_payload=payload,
                    context_session=swarm_context,
                ),
            )
        )
        if isinstance(swarm_result, dict):
            swarm_result["multi_agent_coordination"] = dict(coordination_payload)
            node_env = getattr(o, "_last_node_result_envelope", None)
            node_outcome = getattr(o, "_last_node_outcome", None)
            if isinstance(node_env, dict):
                md_n = node_env.get("metadata")
                if isinstance(md_n, dict):
                    sm_md = swarm_result.get("metadata")
                    swarm_result["metadata"] = {
                        **(sm_md if isinstance(sm_md, dict) else {}),
                        **md_n,
                    }
                ep_n = md_n.get("execution_provenance") if isinstance(md_n, dict) else None
                if isinstance(ep_n, dict):
                    swarm_result["execution_provenance"] = ep_n
                ch_n = node_env.get("cognitive_runtime_hint")
                if isinstance(ch_n, dict):
                    swarm_result["cognitive_runtime_hint"] = ch_n
            if isinstance(node_outcome, dict):
                semantic_lane = str(node_outcome.get("semantic_lane", "") or "").strip()
                if semantic_lane:
                    swarm_result["semantic_runtime_lane"] = semantic_lane
                if bool(node_outcome.get("actions_executed")) or str(
                    node_outcome.get("execution_runtime_lane", "") or ""
                ).strip() == LANE_TRUE_ACTION_EXECUTION:
                    swarm_result["execution_runtime_lane"] = LANE_TRUE_ACTION_EXECUTION
                    swarm_result["true_action_execution_active"] = True
                    swarm_result["compatibility_execution_active"] = False
        return swarm_result


    def dispatch_strategy_execution(
        self,
        *,
        session_id: str,
        run_id: str,
        routing_decision: Any,
        upgrade_artifacts: dict[str, Any],
        selected_tools: list[str] | None,
        direct_response: str,
        node_execute: Any = None,
        local_tool_execute: Any = None,
        planner_execute: Any = None,
        compat_execute: Any,
    ) -> dict[str, Any]:
        o = self._orch
        request = o._build_strategy_execution_request(
            session_id=session_id,
            run_id=run_id,
            routing_decision=routing_decision,
            upgrade_artifacts=upgrade_artifacts,
            selected_tools=selected_tools,
            direct_response=direct_response,
        )
        dispatch_payload = {
            "selected_strategy": request.selected_strategy,
            "manifest_id": request.manifest_id,
            "fallback_allowed": request.fallback_allowed,
            "governance_blocked": request.governance_blocked,
            "manifest_driven_execution": bool(request.manifest),
            "primary_execution_type": str(request.metadata.get("primary_execution_type", "") or ""),
        }
        o.memory_facade.record_event(
            event_type="runtime_strategy_dispatched",
            description="Strategy dispatcher selected an execution path",
            metadata=dispatch_payload,
        )
        o._append_runtime_event(
            event_type="runtime.strategy.dispatch",
            session_id=session_id,
            task_id="",
            run_id=run_id,
            payload=dispatch_payload,
        )
        # Wrap compat_execute to handle synthesis when NodeRuntimeDelegation returns bridge without actions
        original_compat = compat_execute
        def compat_with_synthesis():
            compat_result = original_compat() if original_compat else {}
            # Check if NodeRuntimeDelegation returned bridge without actions (needs synthesis)
            if (isinstance(compat_result, dict) and 
                isinstance(compat_result.get("trace"), dict) and
                compat_result.get("trace", {}).get("metadata", {}).get("fetch_synthesis", False)):
                # Signal synthesis needed - return empty to trigger fallback to compat_with_synthesis
                return {"fetch_synthesis": True}
            return compat_result
        
        try:
            result = o.strategy_dispatcher.dispatch(
                request,
                compat_execute=compat_with_synthesis,
                node_execute=node_execute,
                local_tool_execute=local_tool_execute,
                planner_execute=planner_execute,
            )
        except Exception as exc:
            o.memory_facade.record_event(
                event_type="runtime_strategy_execution_fallback",
                description="Strategy dispatcher failed and fell back to compatibility execution",
                metadata={"reason": "strategy_dispatch_exception", "error": str(exc)[:400]},
            )
            o._append_runtime_event(
                event_type="runtime.strategy.execution.fallback",
                session_id=session_id,
                task_id="",
                run_id=run_id,
                payload={"reason": "strategy_dispatch_exception", "error": str(exc)[:400]},
            )
            fallback_swarm_result = dict(compat_execute() or {})
            fallback_response = str(fallback_swarm_result.get("response", "") or "").strip() or SAFE_FALLBACK_RESPONSE
            result_payload = {
                "selected_strategy": request.selected_strategy,
                "executor_used": "compatibility_path",
                "status": "fallback",
                "response_text": fallback_response,
                "raw_result": fallback_swarm_result,
                "trace": {
                    "selected_strategy": request.selected_strategy,
                    "executor_used": "compatibility_path",
                    "status": "fallback",
                    "manifest_driven_execution": False,
                    "governance_blocked": False,
                    "governance_downgrade_applied": False,
                    "fallback_applied": True,
                    "downgraded": False,
                    "blocked_reason": "",
                    "fallback_reason": "strategy_dispatch_exception",
                    "response_synthesis_mode": "fallback",
                    "observability_tags": list(request.manifest.get("observability_tags", []) or []),
                    "execution_trace_summary": "Compatibility execution path was used after strategy dispatch failure.",
                    "metadata": {"error": str(exc)[:400]},
                },
                "blocked": False,
                "downgraded": False,
                "fallback_applied": True,
                "governance_downgrade_applied": False,
                "manifest_driven_execution": False,
                "response_synthesis_mode": "fallback",
                "error": str(exc)[:400],
                "metadata": {"decision_final_source": "dispatcher_fallback"},
            }
            o.last_strategy_execution = dict(result_payload)
            return result_payload

        result_payload = result.as_dict()
        result_payload.setdefault("selected_strategy", request.selected_strategy)
        result_payload["manifest_id"] = request.manifest_id
        result_payload["strategy_dispatch_applied"] = True
        result_payload["primary_execution_type"] = str(request.metadata.get("primary_execution_type", "") or "")
        result_payload["ranking_source"] = str((o.last_decision_ranking or {}).get("decision_source", "rule") or "rule")
        result_payload["decision_final_source"] = (
            "strategy_dispatch_fallback" if result.fallback_applied else "strategy_dispatch"
        )
        for key in (
            "decision_task_type",
            "decision_reasoning",
            "decision_reason_codes",
            "decision_requires_tools",
            "decision_requires_node_runtime",
            "decision_must_execute",
            "decision_suggested_tools",
            "decision_preferred_capability_path",
        ):
            result_payload[key] = request.metadata.get(key)
        trace_payload = dict(result_payload.get("trace") or {})
        raw_result = dict(result.raw_result or {})
        trace_payload.setdefault("selected_strategy", request.selected_strategy)
        trace_payload["executor_used"] = result.executor_used
        trace_payload["strategy_execution_status"] = result.status
        trace_payload["strategy_execution_fallback"] = bool(result.fallback_applied)
        trace_payload["manifest_driven_execution"] = bool(result.manifest_driven_execution)
        trace_payload["governance_downgrade_applied"] = bool(result.governance_downgrade_applied)
        execution_summary = str(trace_payload.get("execution_trace_summary", "") or "")
        explicit_execution_runtime_lane = str(
            result_payload.get("execution_runtime_lane", "")
            or trace_payload.get("execution_runtime_lane", "")
            or raw_result.get("execution_runtime_lane", "")
            or ""
        ).strip()
        true_action_execution_active = bool(
            raw_result.get("true_action_execution_active")
            or explicit_execution_runtime_lane == LANE_TRUE_ACTION_EXECUTION
        )
        compatibility_execution_active = False if true_action_execution_active else (
            result.executor_used == "compatibility_path"
            or "compatibility runtime path" in execution_summary.lower()
            or "compatibility execution path" in execution_summary.lower()
        )
        if true_action_execution_active:
            trace_payload["execution_trace_summary"] = (
                "Compatibility dispatch promoted node execution_request.actions into the primary true action execution path."
            )
        trace_payload["execution_runtime_lane"] = (
            LANE_TRUE_ACTION_EXECUTION
            if true_action_execution_active
            else explicit_execution_runtime_lane
            or (LANE_COMPATIBILITY_EXECUTION if compatibility_execution_active else "")
        )
        trace_payload["compatibility_execution_active"] = compatibility_execution_active
        trace_payload["true_action_execution_active"] = true_action_execution_active
        trace_payload["primary_execution_type"] = str(request.metadata.get("primary_execution_type", "") or "")
        trace_payload["decision_reasoning"] = str(request.metadata.get("decision_reasoning", "") or "")
        trace_payload["decision_reason_codes"] = list(request.metadata.get("decision_reason_codes", []) or [])
        trace_payload["decision_must_execute"] = bool(request.metadata.get("decision_must_execute", False))
        trace_payload["decision_suggested_tools"] = list(request.metadata.get("decision_suggested_tools", []) or [])
        result_payload["trace"] = trace_payload
        result_payload["execution_runtime_lane"] = trace_payload["execution_runtime_lane"]
        result_payload["compatibility_execution_active"] = compatibility_execution_active
        result_payload["true_action_execution_active"] = true_action_execution_active
        result_payload["execution_path_used"] = str(trace_payload.get("metadata", {}).get("execution_path_used", "") or "")
        tool_execution, tool_diagnostics = summarize_tool_execution(
            step_results=raw_result.get("step_results") if isinstance(raw_result.get("step_results"), list) else None,
            selected_tools=list(request.metadata.get("selected_tools", []) or []),
        )
        if tool_execution is None and isinstance(getattr(o, "_last_tool_execution", None), dict):
            tool_execution = dict(o._last_tool_execution)
        if not tool_diagnostics and isinstance(getattr(o, "_last_tool_diagnostics", None), list):
            tool_diagnostics = [dict(item) for item in o._last_tool_diagnostics if isinstance(item, dict)]
        if tool_execution is not None:
            result_payload["tool_execution"] = tool_execution
            trace_payload["tool_execution"] = tool_execution
        if tool_diagnostics:
            result_payload["tool_diagnostics"] = tool_diagnostics
            trace_payload["tool_diagnostics"] = tool_diagnostics

        event_type = "runtime_strategy_execution_blocked" if result.blocked else "runtime_strategy_executed"
        event_desc = (
            "Strategy execution blocked by guardrails"
            if result.blocked
            else "Strategy executor completed a manifest-driven execution path"
        )
        o.memory_facade.record_event(event_type=event_type, description=event_desc, metadata=trace_payload)
        o._append_runtime_event(
            event_type="runtime.strategy.execution.result",
            session_id=session_id,
            task_id="",
            run_id=run_id,
            payload=trace_payload,
        )
        if result.fallback_applied:
            o.memory_facade.record_event(
                event_type="runtime_strategy_execution_fallback",
                description="Strategy execution degraded to a safe fallback",
                metadata=trace_payload,
            )
            o._append_runtime_event(
                event_type="runtime.strategy.execution.fallback",
                session_id=session_id,
                task_id="",
                run_id=run_id,
                payload=trace_payload,
            )
        if result.manifest_driven_execution:
            o.memory_facade.record_event(
                event_type="runtime_manifest_execution_applied",
                description="Execution manifest directly influenced the runtime path",
                metadata={
                    "manifest_id": request.manifest_id,
                    "selected_strategy": request.selected_strategy,
                    "response_synthesis_mode": result.response_synthesis_mode,
                },
            )
        o.last_strategy_execution = dict(result_payload)
        return result_payload

