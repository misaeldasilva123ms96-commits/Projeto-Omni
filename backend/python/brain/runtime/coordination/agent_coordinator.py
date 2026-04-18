from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from .agent_roles import ROLE_ORDER, SpecialistRuntimeRole
from .coordination_models import CoordinationResult, MultiAgentCoordinationTrace, SpecialistParticipation
from .coordination_state import CoordinationState


def _coordination_fingerprint(
    *,
    session_id: str,
    run_id: str,
    plan_id: str,
    mode: str,
) -> str:
    raw = json.dumps(
        {"session_id": session_id, "run_id": run_id, "plan_id": plan_id, "mode": mode},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _new_coordination_id(*, fingerprint: str) -> str:
    return f"mac37-{fingerprint[:12]}-{uuid.uuid4().hex[:10]}"


def _plan_dict(planning_payload: dict[str, Any]) -> dict[str, Any]:
    ep = planning_payload.get("execution_plan")
    return dict(ep) if isinstance(ep, dict) else {}


def _reasoning_trace_id(reasoning_payload: dict[str, Any]) -> str:
    tr = reasoning_payload.get("trace")
    if isinstance(tr, dict):
        tid = str(tr.get("trace_id", "")).strip()
        if tid:
            return tid
    return ""


def _strategy_trace_id(strategy_payload: dict[str, Any]) -> str:
    st = strategy_payload.get("strategy_trace")
    if isinstance(st, dict):
        tid = str(st.get("trace_id", "")).strip()
        if tid:
            return tid
    return ""


class AgentCoordinator:
    """Phase 37 — bounded multi-agent coordination between planning and execution (advisory to control)."""

    def coordinate(
        self,
        *,
        session_id: str,
        run_id: str,
        planning_payload: dict[str, Any],
        reasoning_handoff: dict[str, Any],
        reasoning_payload: dict[str, Any],
        memory_context_payload: dict[str, Any],
        strategy_payload: dict[str, Any],
        control_execution_summary: dict[str, Any],
        coordination_mode: str,
    ) -> CoordinationResult:
        """
        control_execution_summary must reflect control layer truth. Coordinator never flips allow/block.
        coordination_mode: 'full' | 'skipped_direct_memory'
        """
        degraded = False
        err = ""
        participations: list[SpecialistParticipation] = []
        issues_aggregate: list[str] = []

        allowed = bool(control_execution_summary.get("allowed", True))
        plan = _plan_dict(planning_payload)
        plan_id = str(plan.get("plan_id", "") or "").strip()
        fp = _coordination_fingerprint(
            session_id=session_id or "",
            run_id=run_id or "",
            plan_id=plan_id or "noplan",
            mode=coordination_mode,
        )
        cid = _new_coordination_id(fingerprint=fp)

        state = CoordinationState(
            coordination_id=cid,
            coordination_fingerprint=fp,
            session_id=str(session_id or ""),
            run_id=str(run_id or ""),
            plan_id=plan_id,
            memory_context_id=str(memory_context_payload.get("context_id", "") or ""),
            strategy_trace_id=_strategy_trace_id(strategy_payload),
            coordination_mode=coordination_mode,
            control_execution_allowed=allowed,
            control_reason_code=str(control_execution_summary.get("reason_code", "") or ""),
            routing_task_type=str(control_execution_summary.get("task_type", "") or ""),
            routing_risk_level=str(control_execution_summary.get("risk_level", "") or ""),
            routing_execution_strategy=str(control_execution_summary.get("execution_strategy", "") or ""),
            routing_verification_intensity=str(control_execution_summary.get("verification_intensity", "") or ""),
            reasoning_trace_id=_reasoning_trace_id(reasoning_payload),
        )

        try:
            if coordination_mode == "skipped_direct_memory":
                for role in ROLE_ORDER:
                    participations.append(
                        SpecialistParticipation(
                            role=role.value,
                            status="skipped",
                            input_ref="n/a",
                            output_summary="Coordination skipped: direct memory short-circuit (no swarm boundary).",
                            recommended_next_step="none",
                        )
                    )
                trace = MultiAgentCoordinationTrace(
                    coordination_id=cid,
                    session_id=state.session_id,
                    run_id=state.run_id,
                    coordination_mode=coordination_mode,
                    role_order=[r.value for r in ROLE_ORDER],
                    participations=participations,
                    execution_readiness="not_applicable",
                    governance_authority_preserved=True,
                    control_execution_allowed=allowed,
                    issues_aggregate=[],
                    degraded=False,
                    error="",
                    summary="Coordination bypassed for direct-memory response path.",
                )
                bundle = {
                    "phase": "37",
                    "coordination_id": cid,
                    "execution_readiness": trace.execution_readiness,
                    "governance_authority_preserved": True,
                    "control_execution_allowed": allowed,
                    "specialist_digest": {},
                    "state": state.as_dict(),
                }
                return CoordinationResult(trace=trace, handoff_bundle=bundle)

            if not allowed:
                # Defensive: orchestrator should not invoke this when blocked; remain governance-safe.
                participations.append(
                    SpecialistParticipation(
                        role=SpecialistRuntimeRole.VALIDATOR.value,
                        status="blocked",
                        input_ref="control_execution_summary",
                        output_summary="Control layer disallowed execution; coordination records advisory state only.",
                        issues=["execution_not_allowed_by_control_plane"],
                        recommended_next_step="await_operator_or_policy_resolution",
                    )
                )
                issues_aggregate.append("execution_not_allowed_by_control_plane")
                trace = MultiAgentCoordinationTrace(
                    coordination_id=cid,
                    session_id=state.session_id,
                    run_id=state.run_id,
                    coordination_mode=coordination_mode,
                    role_order=[SpecialistRuntimeRole.VALIDATOR.value],
                    participations=participations,
                    execution_readiness="blocked_by_control",
                    governance_authority_preserved=True,
                    control_execution_allowed=False,
                    issues_aggregate=list(issues_aggregate),
                    degraded=False,
                    error="",
                    summary="Governance blocked execution; coordinator emits trace only (no execution enrichment).",
                )
                return CoordinationResult(
                    trace=trace,
                    handoff_bundle={
                        "phase": "37",
                        "coordination_id": cid,
                        "execution_readiness": trace.execution_readiness,
                        "governance_authority_preserved": True,
                        "control_execution_allowed": False,
                        "specialist_digest": {},
                        "state": state.as_dict(),
                    },
                )

            planner_out = self._run_planner(state, plan, planning_payload)
            participations.append(planner_out)

            executor_out = self._run_executor(state, plan, reasoning_handoff)
            participations.append(executor_out)

            validator_out = self._run_validator(state, plan, reasoning_handoff, control_execution_summary)
            participations.append(validator_out)
            issues_aggregate.extend(list(validator_out.issues))

            critic_out = self._run_critic(state, control_execution_summary, validator_out)
            participations.append(critic_out)
            issues_aggregate.extend(list(critic_out.issues))

            readiness = self._derive_readiness(validator_out, critic_out, plan)

            summary = (
                f"Roles={len(participations)} readiness={readiness} "
                f"issues={len(issues_aggregate)} plan_id={state.plan_id or 'none'}"
            )
            trace = MultiAgentCoordinationTrace(
                coordination_id=cid,
                session_id=state.session_id,
                run_id=state.run_id,
                coordination_mode=coordination_mode,
                role_order=[p.role for p in participations],
                participations=participations,
                execution_readiness=readiness,
                governance_authority_preserved=True,
                control_execution_allowed=True,
                issues_aggregate=list(dict.fromkeys(issues_aggregate)),
                degraded=degraded,
                error=err,
                summary=summary,
            )
            digest = {
                "planner": {"planning_focus": planner_out.output_summary[:280]},
                "executor": {
                    "prep_hints": executor_out.warnings[:8],
                    "recommended_next_step": executor_out.recommended_next_step,
                },
                "validator": {"issues": validator_out.issues[:12]},
                "critic": {"risks": critic_out.warnings[:12]},
            }
            bundle = {
                "phase": "37",
                "coordination_id": cid,
                "execution_readiness": readiness,
                "governance_authority_preserved": True,
                "control_execution_allowed": True,
                "specialist_digest": digest,
                "accumulated_notes": list(state.specialist_notes)[:24],
                "state": state.as_dict(),
            }
            return CoordinationResult(trace=trace, handoff_bundle=bundle)
        except Exception as exc:
            degraded = True
            err = str(exc)
            fallback_roles = [r.value for r in ROLE_ORDER]
            trace = MultiAgentCoordinationTrace(
                coordination_id=cid,
                session_id=state.session_id,
                run_id=state.run_id,
                coordination_mode=coordination_mode,
                role_order=fallback_roles,
                participations=list(participations),
                execution_readiness="degraded",
                governance_authority_preserved=True,
                control_execution_allowed=allowed,
                issues_aggregate=list(issues_aggregate) + ["coordination_engine_exception"],
                degraded=True,
                error=err,
                summary="Coordination degraded; runtime continues with empty enrichment.",
            )
            return CoordinationResult(
                trace=trace,
                handoff_bundle={
                    "phase": "37",
                    "coordination_id": cid,
                    "execution_readiness": "degraded",
                    "governance_authority_preserved": True,
                    "control_execution_allowed": allowed,
                    "specialist_digest": {},
                    "state": state.as_dict(),
                    "fallback": True,
                },
            )

    @staticmethod
    def _run_planner(
        state: CoordinationState,
        plan: dict[str, Any],
        planning_payload: dict[str, Any],
    ) -> SpecialistParticipation:
        steps = plan.get("steps") if isinstance(plan.get("steps"), list) else []
        step_count = len(steps)
        summary_plan = str(plan.get("planning_summary", "") or "").strip()[:200]
        pt = planning_payload.get("planning_trace")
        trace_steps = int(pt.get("step_count", 0) or 0) if isinstance(pt, dict) else 0
        state.record_note(f"planner:steps={step_count}")
        return SpecialistParticipation(
            role=SpecialistRuntimeRole.PLANNER.value,
            status="completed",
            input_ref="planning_payload.execution_plan",
            output_summary=(
                f"Structured plan: {step_count} step(s); planning_trace_steps={trace_steps}; "
                f"summary={summary_plan or 'n/a'}"
            ),
            warnings=[],
            issues=[],
            recommended_next_step="executor_prepare_handoff",
        )

    @staticmethod
    def _run_executor(
        state: CoordinationState,
        plan: dict[str, Any],
        reasoning_handoff: dict[str, Any],
    ) -> SpecialistParticipation:
        caps = reasoning_handoff.get("suggested_capabilities") if isinstance(reasoning_handoff.get("suggested_capabilities"), list) else []
        cap_names = [str(c).strip() for c in caps[:12] if str(c).strip()]
        requires_validation_steps = 0
        for step in plan.get("steps", []) if isinstance(plan.get("steps"), list) else []:
            if isinstance(step, dict) and bool(step.get("requires_validation")):
                requires_validation_steps += 1
        hints = []
        if requires_validation_steps:
            hints.append(f"{requires_validation_steps}_steps_require_validation")
        if cap_names:
            hints.append(f"capabilities:{','.join(cap_names[:6])}")
        state.record_note("executor:handoff_prepared")
        return SpecialistParticipation(
            role=SpecialistRuntimeRole.EXECUTOR.value,
            status="completed",
            input_ref="reasoning_handoff.suggested_capabilities+execution_plan.steps",
            output_summary="Execution-oriented handoff: capability alignment and validation hooks enumerated.",
            warnings=hints,
            issues=[],
            recommended_next_step="validator_consistency_check",
        )

    @staticmethod
    def _run_validator(
        state: CoordinationState,
        plan: dict[str, Any],
        reasoning_handoff: dict[str, Any],
        control_execution_summary: dict[str, Any],
    ) -> SpecialistParticipation:
        issues: list[str] = []
        if not bool(reasoning_handoff.get("proceed", True)):
            issues.append("reasoning_handoff_proceed_false")
        hand_task = str(reasoning_handoff.get("task_type", "") or "").strip()
        route_task = str(control_execution_summary.get("task_type", "") or "").strip()
        if hand_task and route_task and hand_task != route_task:
            issues.append(f"task_type_mismatch_handoff:{hand_task}_vs_routing:{route_task}")
        plan_intent = str(plan.get("primary_intent", "") or "").strip()
        hint_intent = str(reasoning_handoff.get("intent", "") or "").strip()
        if plan_intent and hint_intent and plan_intent != hint_intent:
            issues.append("intent_divergence_plan_vs_handoff")
        if not plan.get("plan_id"):
            issues.append("missing_plan_id")
        if isinstance(plan.get("steps"), list) and len(plan["steps"]) == 0:
            issues.append("empty_execution_plan_steps")
        status = "completed" if not issues else "completed_with_issues"
        state.record_note(f"validator:issues={len(issues)}")
        return SpecialistParticipation(
            role=SpecialistRuntimeRole.VALIDATOR.value,
            status=status,
            input_ref="reasoning_handoff+execution_plan+control_routing",
            output_summary=f"Consistency check: {len(issues)} issue(s).",
            warnings=[],
            issues=issues,
            recommended_next_step="critic_risk_review" if not issues else "review_issues_before_execution",
        )

    @staticmethod
    def _run_critic(
        state: CoordinationState,
        control_execution_summary: dict[str, Any],
        validator: SpecialistParticipation,
    ) -> SpecialistParticipation:
        risks: list[str] = []
        risk = str(control_execution_summary.get("risk_level", "") or "").lower()
        if risk in ("high", "critical"):
            risks.append(f"elevated_risk_level:{risk}")
        ver = str(control_execution_summary.get("verification_intensity", "") or "").lower()
        if ver in ("strict", "maximum"):
            risks.append(f"strict_verification:{ver}")
        if validator.issues:
            risks.append("validator_reported_issues")
        state.record_note("critic:risks_scanned")
        return SpecialistParticipation(
            role=SpecialistRuntimeRole.CRITIC.value,
            status="completed",
            input_ref="control_routing+validator_output",
            output_summary=f"Risk scan: {len(risks)} signal(s).",
            warnings=risks,
            issues=[],
            recommended_next_step="proceed_with_governed_execution" if not risks else "monitor_and_verify",
        )

    @staticmethod
    def _derive_readiness(
        validator: SpecialistParticipation,
        critic: SpecialistParticipation,
        plan: dict[str, Any],
    ) -> str:
        if validator.issues:
            return "advisory_review"
        if critic.warnings:
            return "ready_with_risk_signals"
        if bool(plan.get("execution_ready", False)):
            return "ready"
        return "ready_degraded_plan_flag"
