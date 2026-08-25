"""Runtime action loop extracted from BrainOrchestrator (Phase 2 decomposition).

Owns the step-by-step execution of planned actions: control-layer clearance,
plan graph / execution tree bookkeeping, engineering data collection,
continuation handling, and checkpointing. Strategy selection and single-action
execution remain on the orchestrator; this service coordinates them.
"""

from __future__ import annotations

from typing import Any

from brain.env import read_env
from brain.runtime.control import RunStatus
from brain.runtime.execution_state import build_execution_state
from brain.runtime.observability.tool_execution_diagnostics import summarize_tool_execution
from brain.runtime.serializers import (
    bundle_to_dict,
    evidence_to_dict,
    policy_result_to_dict,
)

MUTATING_TOOLS = {
    "write_file",
    "filesystem_write",
    "git_commit",
    "package_manager",
    "autonomous_debug_loop",
    "filesystem_patch_set",
    "shell_command",
}
VERIFICATION_TOOLS = {"test_runner", "verification_runner"}


class ActionExecutionService:
    """Coordinates the runtime action loop on behalf of BrainOrchestrator."""

    __slots__ = ("_orch",)

    def __init__(self, orchestrator: object) -> None:
        self._orch = orchestrator

    def execute_runtime_actions(
        self,
        *,
        session_id: str,
        message: str,
        actions: list[dict[str, Any]],
        task_id: str,
        run_id: str,
        provider: dict[str, Any] | str,
        intent: str,
        delegation: dict[str, Any],
        critic_review: dict[str, Any] | None = None,
        plan_kind: str = "linear",
        plan_graph: dict[str, Any] | None = None,
        semantic_retrieval: object = None,
        plan_hierarchy: dict[str, Any] | None = None,
        learning_guidance: object = None,
        policy_summary: object = None,
        branch_plan: dict[str, Any] | None = None,
        simulation_summary: dict[str, Any] | None = None,
        cooperative_plan: dict[str, Any] | None = None,
        strategy_suggestions: object = None,
        execution_tree: dict[str, Any] | None = None,
        negotiation_summary: dict[str, Any] | None = None,
        strategy_optimization: dict[str, Any] | None = None,
        repository_analysis: dict[str, Any] | None = None,
        repo_impact_analysis: dict[str, Any] | None = None,
        verification_plan: dict[str, Any] | None = None,
        verification_selection: dict[str, Any] | None = None,
        milestone_plan: dict[str, Any] | None = None,
        engineering_review: dict[str, Any] | None = None,
        engineering_workflow: dict[str, Any] | None = None,
        start_index: int = 0,
        operator_control_enabled: bool = False,
    ) -> list[dict[str, Any]]:
        o = self._orch
        max_steps = min(len(actions), int(read_env("OMNI_MAX_STEPS", "6") or "6"))
        step_results: list[dict[str, Any]] = []
        critic_review = critic_review or {}
        graph_state = o._clone_plan_graph(plan_graph)
        tree_state = o._clone_tree(execution_tree)
        plan_signature = o._plan_signature(actions, graph_state)
        branch_state = o._initial_branch_state(branch_plan)
        engineering_data: dict[str, Any] = {
            "repository_analysis": repository_analysis or {},
            "repo_impact_analysis": repo_impact_analysis or {},
            "impact_map": (repo_impact_analysis or {}).get("impact_map", {}),
            "verification_plan": verification_plan or {},
            "verification_selection": verification_selection or {},
            "milestone_plan": milestone_plan or {},
            "milestone_state": o.milestone_tracker.load_plan(milestone_plan),
            "engineering_review": engineering_review or {},
            "engineering_workflow": engineering_workflow or {},
            "workspace_state": {},
            "patch_history": [],
            "patch_sets": [],
            "debug_iterations": [],
            "test_results": {},
            "verification_summary": {},
            "pr_summary": {},
        }
        o._register_run_record(
            run_id=run_id,
            session_id=session_id,
            goal_id=None,
            status=RunStatus.RUNNING,
            last_action="execution_started",
            progress_score=0.0,
            metadata={
                "task_id": task_id,
                "intent": intent,
                "plan_kind": plan_kind,
                "operator_control_enabled": operator_control_enabled,
            },
        )
        planning_decision, operational_plan = o.planning_executor.ensure_plan(
            session_id=session_id,
            task_id=task_id,
            run_id=run_id,
            message=message,
            actions=actions,
            plan_kind=plan_kind,
            branch_plan=branch_plan,
            start_index=start_index,
            engineering_workflow=engineering_workflow,
            advisory_signals=[signal.as_dict() for signal in o.learning_executor.advisory_signals_for_planning(actions=actions)],
        )
        action_lookup = {
            str(action.get("step_id", "")).strip(): action
            for action in actions
            if isinstance(action, dict) and str(action.get("step_id", "")).strip()
        }
        o._append_runtime_event(
            event_type="runtime.planning.classification",
            session_id=session_id,
            task_id=task_id,
            run_id=run_id,
            payload={
                "classification": planning_decision.as_dict(),
                "plan_id": operational_plan.plan_id if operational_plan else None,
            },
        )
        goal_context = o.planning_executor.goal_context_for_plan(operational_plan)
        o._register_run_record(
            run_id=run_id,
            session_id=session_id,
            goal_id=getattr(operational_plan, "goal_id", None),
            status=RunStatus.RUNNING,
            last_action="plan_initialized",
            progress_score=0.0,
            metadata={
                "task_id": task_id,
                "intent": intent,
                "plan_id": getattr(operational_plan, "plan_id", ""),
                "plan_kind": plan_kind,
            },
        )
        if operational_plan is not None and operational_plan.goal_id:
            o.memory_facade.set_active_goal(
                session_id=session_id,
                goal_id=operational_plan.goal_id,
                active_plan_id=operational_plan.plan_id,
                goal_context=goal_context,
            )
            o.memory_facade.record_event(
                event_type="plan_initialized",
                description=planning_decision.summary,
                outcome=operational_plan.status.value,
                progress_score=0.0,
                metadata={
                    "plan_id": operational_plan.plan_id,
                    "task_id": operational_plan.task_id,
                    "goal_id": operational_plan.goal_id,
                    "classification": planning_decision.classification.value,
                },
            )
        control_metadata = o._build_control_metadata(
            message=message,
            actions=actions,
            metadata={
                "control_boundary": "action_execution",
                "requested_action": "test"
                if any(str(action.get("selected_tool", "")) in VERIFICATION_TOOLS for action in actions)
                else "mutate"
                if any(str(action.get("selected_tool", "")) in MUTATING_TOOLS for action in actions)
                else "execute",
            },
            repository_analysis=repository_analysis,
            repo_impact_analysis=repo_impact_analysis,
            verification_plan=verification_plan,
            engineering_data=engineering_data,
            policy_summary=policy_summary,
        )
        control_result = o._evaluate_control_layer(
            session_id=session_id,
            message=message,
            task_id=task_id,
            run_id=run_id,
            metadata=control_metadata,
        )
        upgrade_artifacts = o._build_runtime_upgrade_artifacts(
            message=message,
            session_id=session_id,
            run_id=run_id,
            routing_decision=control_result["routing_decision"],
            strategy_payload={},
            selected_tools=control_metadata.get("selected_tools", []),
            provider_path="",
        )
        control_metadata["oil_summary"] = dict(upgrade_artifacts.get("oil_summary") or {})
        control_metadata["routing_decision_record"] = dict(upgrade_artifacts.get("routing_record") or {})
        control_metadata["execution_manifest"] = dict(upgrade_artifacts.get("manifest") or {})
        control_metadata["fallback_triggered"] = bool(upgrade_artifacts.get("fallback_triggered"))
        context_budget, retrieval_plan = o._build_context_budget(
            routing_decision=control_result["routing_decision"]
        )
        o._update_structured_memory(
            session_id=session_id,
            task_id=task_id,
            run_id=run_id,
            message=message,
            control_metadata=control_metadata,
            control_result=control_result,
            budget=context_budget,
            retrieval_plan=retrieval_plan,
        )
        o._record_runtime_upgrade_events(
            session_id=session_id,
            task_id=task_id,
            run_id=run_id,
            upgrade_artifacts=upgrade_artifacts,
        )
        o._emit_control_event(
            "runtime.control.routing_decision",
            session_id=session_id,
            task_id=task_id,
            run_id=run_id,
            payload={
                "control_mode": o.current_control_mode.value,
                "task_type": control_result["routing_decision"].task_type,
                "capability_path": control_result["routing_decision"].preferred_capability_path,
                "risk_level": control_result["routing_decision"].risk_level,
                "execution_strategy": control_result["routing_decision"].execution_strategy,
                "verification_intensity": control_result["routing_decision"].verification_intensity,
                "recommended_specialists": control_result["routing_decision"].recommended_specialists,
                "delegation_recommended": control_result["routing_decision"].specialist_delegation_recommended,
                "routing_reason": control_result["routing_decision"].reasoning,
                "allowed": control_result["allowed"],
            },
        )
        if not control_result["allowed"]:
            o._record_control_outcome_memory(
                session_id=session_id,
                task_id=task_id,
                run_id=run_id,
                control_result=control_result,
                allowed=False,
            )
            o._emit_control_event(
                str(control_result["blocked_event_type"]),
                session_id=session_id,
                task_id=task_id,
                run_id=run_id,
                payload={
                    "control_mode": o.current_control_mode.value,
                    "task_type": control_result["routing_decision"].task_type,
                    "capability_path": control_result["routing_decision"].preferred_capability_path,
                    "risk_level": control_result["routing_decision"].risk_level,
                    "execution_strategy": control_result["routing_decision"].execution_strategy,
                    "verification_intensity": control_result["routing_decision"].verification_intensity,
                    "recommended_specialists": control_result["routing_decision"].recommended_specialists,
                    "delegation_recommended": control_result["routing_decision"].specialist_delegation_recommended,
                    "routing_reason": control_result["routing_decision"].reasoning,
                    "policy_results": [policy_result_to_dict(item) for item in control_result["policy_result"].results],
                    "missing_evidence_types": control_result["evidence_result"].missing_evidence_types,
                    "reason_code": control_result["blocked_reason_code"],
                    "allowed": False,
                },
            )
            blocked = {
                "ok": False,
                "selected_tool": "none",
                "selected_agent": "master_orchestrator",
                "error_payload": {
                    "kind": "control_layer_block",
                    "message": str(control_result["blocked_response"]),
                    "reason_code": str(control_result["blocked_reason_code"]),
                    "policy_results": [policy_result_to_dict(item) for item in control_result["policy_result"].results],
                    "missing_evidence_types": control_result["evidence_result"].missing_evidence_types,
                },
                "evaluation": {
                    "decision": "stop_blocked",
                    "reason_code": str(control_result["blocked_reason_code"]),
                    "control_layer": {
                        "routing": control_result["routing_decision"].as_dict(),
                        "evidence": evidence_to_dict(control_result["evidence_result"]),
                        "policy": bundle_to_dict(control_result["policy_result"]),
                    },
                },
            }
            step_results.append(blocked)
            o._write_checkpoint(
                run_id=run_id,
                task_id=task_id,
                session_id=session_id,
                message=message,
                actions=actions,
                next_step_index=start_index,
                completed_steps=step_results,
                plan_graph=graph_state,
                plan_hierarchy=plan_hierarchy,
                plan_signature=plan_signature,
                status="blocked",
                branch_state=branch_state,
                simulation_summary=simulation_summary,
                cooperative_plan=cooperative_plan,
                strategy_suggestions=strategy_suggestions,
                policy_summary=policy_summary,
                execution_tree=tree_state,
                negotiation_summary=negotiation_summary,
                strategy_optimization=strategy_optimization,
                supervision={"control_layer": blocked["evaluation"]["control_layer"]},
                repository_analysis=repository_analysis,
                engineering_data=engineering_data,
            )
            operational_plan = o.planning_executor.finalize_plan(
                operational_plan,
                status_hint="blocked",
                step_results=step_results,
            )
            o._update_run_status(
                run_id=run_id,
                status=RunStatus.FAILED,
                last_action="control_layer_blocked",
                progress_score=o._progress_from_step_results(step_results),
            )
            o._last_tool_execution = None
            o._last_tool_diagnostics = []
            o._last_runtime_step_results = []
            return step_results
        if control_result["mode_transition"] is not None:
            o._emit_control_event(
                "runtime.control.mode_transition",
                session_id=session_id,
                task_id=task_id,
                run_id=run_id,
                payload=control_result["mode_transition"],
            )
            o.current_control_mode = control_result["target_mode"]
        o._record_control_outcome_memory(
            session_id=session_id,
            task_id=task_id,
            run_id=run_id,
            control_result=control_result,
            allowed=True,
        )
        o._emit_control_event(
            "runtime.control.execution_allowed",
            session_id=session_id,
            task_id=task_id,
            run_id=run_id,
            payload={
                "control_mode": o.current_control_mode.value,
                "task_type": control_result["routing_decision"].task_type,
                "capability_path": control_result["routing_decision"].preferred_capability_path,
                "risk_level": control_result["routing_decision"].risk_level,
                "execution_strategy": control_result["routing_decision"].execution_strategy,
                "verification_intensity": control_result["routing_decision"].verification_intensity,
                "recommended_specialists": control_result["routing_decision"].recommended_specialists,
                "delegation_recommended": control_result["routing_decision"].specialist_delegation_recommended,
                "routing_reason": control_result["routing_decision"].reasoning,
                "policy_results": [policy_result_to_dict(item) for item in control_result["policy_result"].results],
                "missing_evidence_types": control_result["evidence_result"].missing_evidence_types,
                "reason_code": "execution_allowed",
                "allowed": True,
            },
        )
        supervision = o.supervisor.inspect(
            execution_tree=tree_state,
            branch_plan=branch_plan,
            negotiation_summary=negotiation_summary,
            executed_steps=0,
            max_steps=max_steps,
        )
        if critic_review.get("invoked"):
            o._append_runtime_event(
                event_type="runtime.critic.plan",
                session_id=session_id,
                task_id=task_id,
                run_id=run_id,
                payload={
                    "critic_review": critic_review,
                    "plan_kind": plan_kind,
                },
            )
        if plan_kind == "graph" and isinstance(graph_state, dict):
            o._append_runtime_event(
                event_type="runtime.graph.plan",
                session_id=session_id,
                task_id=task_id,
                run_id=run_id,
                payload={
                    "plan_kind": plan_kind,
                    "node_count": len(graph_state.get("nodes", [])),
                },
            )
        if plan_kind == "hierarchical" and isinstance(plan_hierarchy, dict):
            o._append_runtime_event(
                event_type="runtime.goal.plan",
                session_id=session_id,
                task_id=task_id,
                run_id=run_id,
                payload={
                    "root_goal_id": plan_hierarchy.get("root_goal_id"),
                    "subgoal_count": len(plan_hierarchy.get("subgoals", []))
                    if isinstance(plan_hierarchy.get("subgoals", []), list)
                    else 0,
                },
            )
        if isinstance(cooperative_plan, dict):
            o._append_runtime_event(
                event_type="runtime.cooperation.plan",
                session_id=session_id,
                task_id=task_id,
                run_id=run_id,
                payload={
                    "shared_goal_id": cooperative_plan.get("shared_goal_id"),
                    "contribution_count": len(cooperative_plan.get("contributions", [])),
                },
            )
        if isinstance(negotiation_summary, dict):
            o._append_runtime_event(
                event_type="runtime.negotiation.summary",
                session_id=session_id,
                task_id=task_id,
                run_id=run_id,
                payload={
                    "final_decision": negotiation_summary.get("final_decision"),
                    "disagreement_count": negotiation_summary.get("disagreement_count", 0),
                },
            )
        if isinstance(strategy_optimization, dict):
            o._append_runtime_event(
                event_type="runtime.strategy.optimization",
                session_id=session_id,
                task_id=task_id,
                run_id=run_id,
                payload=strategy_optimization,
            )
        if supervision.get("alerts"):
            o._append_runtime_event(
                event_type="runtime.supervision.alert",
                session_id=session_id,
                task_id=task_id,
                run_id=run_id,
                payload=supervision,
            )
        if supervision.get("stop_execution"):
            blocked = {
                "ok": False,
                "selected_tool": "none",
                "selected_agent": "master_orchestrator",
                "error_payload": {
                    "kind": "supervision_stop",
                    "message": "Execution blocked by cognitive supervision.",
                },
                "evaluation": {"decision": "stop_blocked", "reason_code": "supervision_stop"},
            }
            step_results.append(blocked)
            o._write_checkpoint(
                run_id=run_id,
                task_id=task_id,
                session_id=session_id,
                message=message,
                actions=actions,
                next_step_index=start_index,
                completed_steps=step_results,
                plan_graph=graph_state,
                plan_hierarchy=plan_hierarchy,
                plan_signature=plan_signature,
                status="blocked",
                branch_state=branch_state,
                simulation_summary=simulation_summary,
                cooperative_plan=cooperative_plan,
                strategy_suggestions=strategy_suggestions,
                policy_summary=policy_summary,
                execution_tree=tree_state,
                negotiation_summary=negotiation_summary,
                strategy_optimization=strategy_optimization,
                supervision=supervision,
                repository_analysis=repository_analysis,
                engineering_data=engineering_data,
            )
            o._update_run_status(
                run_id=run_id,
                status=RunStatus.FAILED,
                last_action="supervision_stop",
                progress_score=o._progress_from_step_results(step_results),
            )
            return step_results
        if isinstance(simulation_summary, dict) and simulation_summary.get("invoked"):
            o._append_runtime_event(
                event_type="runtime.simulation.review",
                session_id=session_id,
                task_id=task_id,
                run_id=run_id,
                payload=simulation_summary,
            )
            if simulation_summary.get("recommended_decision") == "stop":
                blocked = {
                    "ok": False,
                    "selected_tool": "none",
                    "selected_agent": "critic_agent",
                    "error_payload": {
                        "kind": "simulation_stop",
                        "message": str(simulation_summary.get("summary", "Execution blocked by simulation review.")),
                    },
                    "evaluation": {
                        "decision": "stop_blocked",
                        "reason_code": "simulation_stop",
                    },
                }
                step_results.append(blocked)
                o._write_checkpoint(
                    run_id=run_id,
                    task_id=task_id,
                    session_id=session_id,
                    message=message,
                    actions=actions,
                    next_step_index=start_index,
                    completed_steps=step_results,
                    plan_graph=graph_state,
                    plan_hierarchy=plan_hierarchy,
                    plan_signature=plan_signature,
                    status="blocked",
                    branch_state=branch_state,
                    simulation_summary=simulation_summary,
                    cooperative_plan=cooperative_plan,
                    strategy_suggestions=strategy_suggestions,
                    policy_summary=policy_summary,
                    execution_tree=tree_state,
                    negotiation_summary=negotiation_summary,
                    strategy_optimization=strategy_optimization,
                    supervision=supervision,
                    repository_analysis=repository_analysis,
                    engineering_data=engineering_data,
                )
                o._write_run_summary(
                    session_id=session_id,
                    task_id=task_id,
                    run_id=run_id,
                    message=message,
                    step_results=step_results,
                    plan_kind=plan_kind,
                    plan_hierarchy=plan_hierarchy,
                    reflection={"invoked": False, "reason_code": "simulation_stop"},
                    branch_state=branch_state,
                    cooperative_plan=cooperative_plan,
                    simulation_summary=simulation_summary,
                    strategy_suggestions=strategy_suggestions,
                    fusion_summary=None,
                    policy_summary=policy_summary,
                    execution_tree=tree_state,
                    negotiation_summary=negotiation_summary,
                    strategy_optimization=strategy_optimization,
                    supervision=supervision,
                    execution_state=None,
                    repository_analysis=repository_analysis,
                    engineering_data=engineering_data,
                )
                operational_plan = o.planning_executor.finalize_plan(
                    operational_plan,
                    status_hint="blocked",
                    step_results=step_results,
                )
                o._update_run_status(
                    run_id=run_id,
                    status=RunStatus.FAILED,
                    last_action="simulation_stop",
                    progress_score=o._progress_from_step_results(step_results),
                )
                o._last_tool_execution = None
                o._last_tool_diagnostics = []
                o._last_runtime_step_results = []
                return step_results
        engineering_data = o._finalize_engineering_data(
            message=message,
            engineering_data=o._collect_engineering_data(engineering_data, step_results),
            step_results=step_results,
        )
        o._write_checkpoint(
            run_id=run_id,
            task_id=task_id,
            session_id=session_id,
            message=message,
            actions=actions,
            next_step_index=start_index,
            completed_steps=step_results,
            plan_graph=graph_state,
            plan_hierarchy=plan_hierarchy,
            plan_signature=plan_signature,
            status="running",
            branch_state=branch_state,
            simulation_summary=simulation_summary,
            cooperative_plan=cooperative_plan,
            strategy_suggestions=strategy_suggestions,
            policy_summary=policy_summary,
            execution_tree=tree_state,
            negotiation_summary=negotiation_summary,
            strategy_optimization=strategy_optimization,
            supervision=supervision,
            repository_analysis=repository_analysis,
            engineering_data=engineering_data,
        )
        executed_steps = 0
        branch_action_ids: set[str] = set()
        continuation_stop_requested = False
        if isinstance(branch_plan, dict) and isinstance(branch_state, dict) and branch_state.get("branches"):
            control_state = o._await_run_control_clearance(run_id=run_id)
            if control_state.get("status") != "running":
                blocked = o._control_block_result(
                    reason_code=str(control_state.get("error") or control_state.get("status") or "operator_control_blocked"),
                    message="Execution paused by operator control.",
                )
                step_results.append(blocked)
                o._last_tool_execution = None
                o._last_tool_diagnostics = []
                o._last_runtime_step_results = []
                return step_results
            branch_results, branch_action_ids, branch_state, graph_state, tree_state = o._execute_branch_plan(
                session_id=session_id,
                message=message,
                actions=actions,
                task_id=task_id,
                run_id=run_id,
                provider=provider,
                intent=intent,
                delegation=delegation,
                plan_kind=plan_kind,
                semantic_retrieval=semantic_retrieval,
                plan_hierarchy=plan_hierarchy,
                step_results=step_results,
                branch_plan=branch_plan,
                branch_state=branch_state,
                graph_state=graph_state,
                tree_state=tree_state,
            )
            executed_steps += len(branch_results)
            o._write_checkpoint(
                run_id=run_id,
                task_id=task_id,
                session_id=session_id,
                message=message,
                actions=actions,
                next_step_index=min(start_index + executed_steps, len(actions)),
                completed_steps=step_results,
                plan_graph=graph_state,
                plan_hierarchy=plan_hierarchy,
                plan_signature=plan_signature,
                status="running" if all(item.get("ok") for item in branch_results) else "blocked",
                branch_state=branch_state,
                simulation_summary=simulation_summary,
                cooperative_plan=cooperative_plan,
                strategy_suggestions=strategy_suggestions,
                policy_summary=policy_summary,
                execution_tree=tree_state,
                negotiation_summary=negotiation_summary,
                strategy_optimization=strategy_optimization,
                supervision=supervision,
                repository_analysis=repository_analysis,
                engineering_data=engineering_data,
            )
            for branch_result in branch_results:
                tracked_action = branch_result.get("action", {}) if isinstance(branch_result, dict) else {}
                if not isinstance(tracked_action, dict):
                    tracked_action = action_lookup.get(str(branch_result.get("step_id", "")), {})
                operational_plan = o.planning_executor.record_step_result(
                    operational_plan,
                    action=tracked_action,
                    result=branch_result,
                )
                operational_plan, continuation_payload, should_stop = o._handle_continuation_decision(
                    operational_plan=operational_plan,
                    session_id=session_id,
                    task_id=task_id,
                    run_id=run_id,
                    action=tracked_action if isinstance(tracked_action, dict) else {},
                    result=branch_result,
                )
                if continuation_payload is not None:
                    branch_result["continuation_decision"] = continuation_payload
                if should_stop:
                    continuation_stop_requested = True
                    break
            if continuation_stop_requested or (branch_results and not all(item.get("ok") for item in branch_results)):
                operational_plan = o.planning_executor.finalize_plan(
                    operational_plan,
                    status_hint="blocked",
                    step_results=step_results,
                )
                o._last_runtime_step_results = [dict(item) for item in step_results if isinstance(item, dict)]
                return step_results
        if plan_kind == "graph" and isinstance(graph_state, dict):
            while executed_steps < max_steps:
                control_state = o._await_run_control_clearance(run_id=run_id)
                if control_state.get("status") != "running":
                    blocked = o._control_block_result(
                        reason_code=str(control_state.get("error") or control_state.get("status") or "operator_control_blocked"),
                        message="Execution paused by operator control.",
                    )
                    step_results.append(blocked)
                    break
                batch_stop_requested = False
                ready_parallel, ready_sequential = o._graph_ready_groups(graph_state)
                if not ready_parallel and not ready_sequential:
                    break

                batch_nodes = ready_parallel[: o._runtime_max_parallel_reads()] if ready_parallel else ready_sequential[:1]
                batch_nodes = [node for node in batch_nodes if str(node.get("step_id", "")) not in branch_action_ids]
                if not batch_nodes:
                    break
                batch_actions = [o._action_for_node(actions, node) for node in batch_nodes]
                if any(action is None for action in batch_actions):
                    break

                if len(batch_actions) > 1:
                    o._append_runtime_event(
                        event_type="runtime.parallel.start",
                        session_id=session_id,
                        task_id=task_id,
                        run_id=run_id,
                        payload={
                            "step_ids": [action.get("step_id") for action in batch_actions if isinstance(action, dict)],
                            "parallel_count": len(batch_actions),
                            "plan_kind": plan_kind,
                        },
                    )

                for action in batch_actions:
                    if isinstance(action, dict):
                        operational_plan = o.planning_executor.record_step_started(
                            operational_plan,
                            action=action,
                        )
                batch_results = o._execute_action_batch(
                    actions=[action for action in batch_actions if isinstance(action, dict)],
                    step_results=step_results,
                    semantic_retrieval=semantic_retrieval,
                    learning_guidance=learning_guidance,
                    allow_parallel=len(batch_actions) > 1,
                    session_id=session_id,
                    task_id=task_id,
                    run_id=run_id,
                    operational_plan=operational_plan,
                )

                for action, result in zip(batch_actions, batch_results):
                    executed_steps += 1
                    step_results.append(result)
                    if isinstance(action, dict):
                        operational_plan = o.planning_executor.record_step_result(
                            operational_plan,
                            action=action,
                            result=result,
                        )
                        operational_plan, continuation_payload, should_stop = o._handle_continuation_decision(
                            operational_plan=operational_plan,
                            session_id=session_id,
                            task_id=task_id,
                            run_id=run_id,
                            action=action,
                            result=result,
                        )
                        if continuation_payload is not None:
                            result["continuation_decision"] = continuation_payload
                        if should_stop:
                            batch_stop_requested = True
                            break
                    graph_state = o._mark_graph_outcome(graph_state, action, result)
                    tree_state = o._mark_tree_outcome(tree_state, action, result, retries=len(result.get("correction_events", [])))
                    o._append_runtime_execution_logs(
                        session_id=session_id,
                        message=message,
                        action=action,
                        result=result,
                        task_id=task_id,
                        run_id=run_id,
                        provider=provider,
                        intent=intent,
                        delegates=delegation.get("delegates", []),
                        specialists=delegation.get("specialists", []),
                        plan_kind=plan_kind,
                        semantic_retrieval=semantic_retrieval,
                        plan_hierarchy=plan_hierarchy,
                    )
                    if not result.get("ok"):
                        break

                o._write_checkpoint(
                    run_id=run_id,
                    task_id=task_id,
                    session_id=session_id,
                    message=message,
                    actions=actions,
                    next_step_index=min(start_index + executed_steps, len(actions)),
                    completed_steps=step_results,
                    plan_graph=graph_state,
                    plan_hierarchy=plan_hierarchy,
                    plan_signature=plan_signature,
                    status="blocked" if step_results and not step_results[-1].get("ok") else "running",
                    branch_state=branch_state,
                    simulation_summary=simulation_summary,
                    cooperative_plan=cooperative_plan,
                    strategy_suggestions=strategy_suggestions,
                    policy_summary=policy_summary,
                    execution_tree=tree_state,
                    negotiation_summary=negotiation_summary,
                    strategy_optimization=strategy_optimization,
                    supervision=supervision,
                    repository_analysis=repository_analysis,
                    engineering_data=engineering_data,
                )
                if batch_stop_requested or (step_results and not step_results[-1].get("ok")):
                    break
        else:
            for index, action in enumerate(actions[start_index:max_steps], start=start_index):
                control_state = o._await_run_control_clearance(run_id=run_id)
                if control_state.get("status") != "running":
                    blocked = o._control_block_result(
                        reason_code=str(control_state.get("error") or control_state.get("status") or "operator_control_blocked"),
                        message="Execution paused by operator control.",
                    )
                    step_results.append(blocked)
                    break
                if not isinstance(action, dict):
                    continue
                if str(action.get("step_id", "")) in branch_action_ids:
                    continue

                operational_plan = o.planning_executor.record_step_started(
                    operational_plan,
                    action=action,
                )
                result = o._execute_single_action(
                    action=action,
                    step_results=step_results,
                    semantic_retrieval=semantic_retrieval,
                    learning_guidance=learning_guidance,
                    session_id=session_id,
                    task_id=task_id,
                    run_id=run_id,
                    operational_plan=operational_plan,
                )
                executed_steps += 1
                step_results.append(result)
                operational_plan = o.planning_executor.record_step_result(
                    operational_plan,
                    action=action,
                    result=result,
                )
                operational_plan, continuation_payload, should_stop = o._handle_continuation_decision(
                    operational_plan=operational_plan,
                    session_id=session_id,
                    task_id=task_id,
                    run_id=run_id,
                    action=action,
                    result=result,
                )
                if continuation_payload is not None:
                    result["continuation_decision"] = continuation_payload
                tree_state = o._mark_tree_outcome(tree_state, action, result, retries=len(result.get("correction_events", [])))

                o._append_runtime_execution_logs(
                    session_id=session_id,
                    message=message,
                    action=action,
                    result=result,
                    task_id=task_id,
                    run_id=run_id,
                    provider=provider,
                    intent=intent,
                    delegates=delegation.get("delegates", []),
                    specialists=delegation.get("specialists", []),
                    plan_kind=plan_kind,
                    semantic_retrieval=semantic_retrieval,
                    plan_hierarchy=plan_hierarchy,
                )
                o._write_checkpoint(
                    run_id=run_id,
                    task_id=task_id,
                    session_id=session_id,
                    message=message,
                    actions=actions,
                    next_step_index=index + 1,
                    completed_steps=step_results,
                    plan_graph=graph_state,
                    plan_hierarchy=plan_hierarchy,
                    plan_signature=plan_signature,
                    status="blocked" if not result.get("ok") else "running",
                    branch_state=branch_state,
                    simulation_summary=simulation_summary,
                    cooperative_plan=cooperative_plan,
                    strategy_suggestions=strategy_suggestions,
                    policy_summary=policy_summary,
                    execution_tree=tree_state,
                    negotiation_summary=negotiation_summary,
                    strategy_optimization=strategy_optimization,
                    supervision=supervision,
                    repository_analysis=repository_analysis,
                    engineering_data=engineering_data,
                )

                if should_stop or not result.get("ok"):
                    break

        engineering_data = o._finalize_engineering_data(
            message=message,
            engineering_data=o._collect_engineering_data(engineering_data, step_results),
            step_results=step_results,
        )
        o._write_checkpoint(
            run_id=run_id,
            task_id=task_id,
            session_id=session_id,
            message=message,
            actions=actions,
            next_step_index=min(start_index + len(step_results), len(actions)),
            completed_steps=step_results,
            plan_graph=graph_state,
            plan_hierarchy=plan_hierarchy,
            plan_signature=plan_signature,
            status="completed"
            if (
                (start_index + len(step_results) >= len(actions) or o._graph_complete(graph_state))
                and step_results
                and all(item.get("ok") for item in step_results)
            )
            else "blocked",
            branch_state=branch_state,
            simulation_summary=simulation_summary,
            cooperative_plan=cooperative_plan,
            strategy_suggestions=strategy_suggestions,
            policy_summary=policy_summary,
            execution_tree=tree_state,
            negotiation_summary=negotiation_summary,
            strategy_optimization=strategy_optimization,
            supervision=supervision,
            repository_analysis=repository_analysis,
            engineering_data=engineering_data,
        )
        reflection = o._reflect_on_run(
            message=message,
            step_results=step_results,
            task_id=task_id,
            run_id=run_id,
            session_id=session_id,
            plan_hierarchy=plan_hierarchy,
            learning_guidance=learning_guidance,
            policy_summary=policy_summary,
            branch_state=branch_state,
            cooperative_plan=cooperative_plan,
        )
        if reflection.get("invoked"):
            o._append_runtime_event(
                event_type="runtime.reflection",
                session_id=session_id,
                task_id=task_id,
                run_id=run_id,
                payload=reflection,
            )
            if reflection.get("update_learning"):
                o._record_learning_memory(
                    session_id=session_id,
                    task_id=task_id,
                    run_id=run_id,
                    message=message,
                    outcome="success" if step_results and all(item.get("ok") for item in step_results) else "failure_avoidance",
                    tool_family=str(step_results[0].get("selected_tool", "unknown")) if step_results else "unknown",
                    lesson=str(reflection.get("summary", "")),
                    trigger=str(reflection.get("reason_code", "")),
                    metadata={"plan_kind": plan_kind, "hierarchical": bool(plan_hierarchy)},
                )
        o.checkpoint_store.save(
            run_id,
            {
                "task_id": task_id,
                "session_id": session_id,
                "message": message,
                "status": (
                    "completed"
                    if (
                        min(start_index + len(step_results), len(actions)) >= len(actions)
                        and step_results
                        and all(item.get("ok") for item in step_results)
                    )
                    else "blocked"
                ),
                "next_step_index": min(start_index + len(step_results), len(actions)),
                "completed_steps": step_results,
                "remaining_actions": actions[min(start_index + len(step_results), len(actions)):],
                "total_actions": len(actions),
                "plan_graph": graph_state,
                "plan_hierarchy": plan_hierarchy,
                "plan_signature": plan_signature,
                "reflection_summary": reflection,
                "branch_state": branch_state,
                "simulation_summary": simulation_summary,
                "cooperative_plan": cooperative_plan,
                "strategy_suggestions": strategy_suggestions,
                "policy_summary": policy_summary if isinstance(policy_summary, list) else [],
                "execution_tree": tree_state,
                "negotiation_summary": negotiation_summary,
                "strategy_optimization": strategy_optimization,
                "supervision": supervision,
                "repository_analysis": repository_analysis,
                "engineering_data": engineering_data,
            },
        )
        fusion_summary = o._build_fusion_summary(step_results, cooperative_plan, branch_state, strategy_suggestions)
        execution_state = build_execution_state(
            session_id=session_id,
            task_id=task_id,
            run_id=run_id,
            execution_tree=tree_state,
            branch_state=branch_state,
            cooperative_plan=cooperative_plan,
            negotiation_summary=negotiation_summary,
            simulation_summary=simulation_summary,
            strategy_suggestions=strategy_suggestions if isinstance(strategy_suggestions, list) else [],
            policy_summary=policy_summary if isinstance(policy_summary, list) else [],
            fusion_summary=fusion_summary,
            supervision=supervision,
            repository_analysis=repository_analysis,
            engineering_data=engineering_data,
        )
        o._write_run_summary(
            session_id=session_id,
            task_id=task_id,
            run_id=run_id,
            message=message,
            step_results=step_results,
            plan_kind=plan_kind,
            plan_hierarchy=plan_hierarchy,
            reflection=reflection,
            branch_state=branch_state,
            cooperative_plan=cooperative_plan,
            simulation_summary=simulation_summary,
            strategy_suggestions=strategy_suggestions,
            fusion_summary=fusion_summary,
            policy_summary=policy_summary,
            execution_tree=tree_state,
            negotiation_summary=negotiation_summary,
            strategy_optimization=strategy_optimization,
            supervision=supervision,
            execution_state=execution_state,
            repository_analysis=repository_analysis,
            engineering_data=engineering_data,
        )
        operational_plan = o.planning_executor.finalize_plan(
            operational_plan,
            status_hint="completed" if step_results and all(item.get("ok") for item in step_results) else "blocked",
            step_results=step_results,
        )
        o._completion_service.apply_fusion_terminal_status(run_id=run_id, step_results=step_results)
        operational_summary = o.planning_executor.summary_for_plan(operational_plan)
        if operational_summary is not None:
            final_checkpoint = o.planning_executor.store.load_latest_checkpoint(operational_plan.plan_id) if operational_plan else None
            learning_update = o.learning_executor.ingest_runtime_artifacts(
                plan=operational_plan,
                checkpoint=final_checkpoint,
                summary=operational_summary,
            )
            o._append_runtime_event(
                event_type="runtime.planning.summary",
                session_id=session_id,
                task_id=task_id,
                run_id=run_id,
                payload={
                    **operational_summary.as_dict(),
                    "learning": learning_update,
                },
            )
        tool_execution, tool_diagnostics = summarize_tool_execution(
            step_results=step_results,
            selected_tools=[str(action.get("selected_tool", "") or "").strip() for action in actions if isinstance(action, dict)],
        )
        o._last_tool_execution = tool_execution
        o._last_tool_diagnostics = tool_diagnostics
        o._last_runtime_step_results = [dict(item) for item in step_results if isinstance(item, dict)]
        return step_results

