from __future__ import annotations

import hashlib
from typing import Any
from uuid import uuid4

from brain.runtime.planning.intelligence_models import (
    ExecutionPlan,
    ExecutionPlanStep,
    PlanCheckpointBinding,
    PlanFallbackEdge,
    PlanningTrace,
)
from brain.runtime.planning.models import utc_now_iso

_STAGE_TO_STEP_TYPE: dict[str, str] = {
    "interpret": "analysis",
    "plan": "synthesis",
    "reason": "synthesis",
    "validate": "verification",
    "handoff_to_execution": "execution",
    "memory_contextualization": "context_load",
    "review_assumptions": "verification",
    "risk_gate": "governance",
    "governance_confirmation": "governance",
}


def _slug(s: str, max_len: int = 24) -> str:
    raw = "".join(ch if ch.isalnum() else "-" for ch in (s or "").strip().lower())
    raw = raw.strip("-") or "step"
    return raw[:max_len]


def _topological_order_ok(steps: list[ExecutionPlanStep]) -> bool:
    ids = {s.step_id for s in steps}
    for s in steps:
        if s.step_id in s.depends_on:
            return False
        if any(d not in ids for d in s.depends_on):
            return False
    indegree: dict[str, int] = {s.step_id: 0 for s in steps}
    graph: dict[str, list[str]] = {s.step_id: [] for s in steps}
    for s in steps:
        for dep in s.depends_on:
            graph[dep].append(s.step_id)
            indegree[s.step_id] += 1
    queue = [sid for sid, deg in indegree.items() if deg == 0]
    visited = 0
    while queue:
        n = queue.pop()
        visited += 1
        for nxt in graph.get(n, []):
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)
    return visited == len(steps)


class PlanningEngine:
    """Phase 33 — turns reasoning handoff into a dependency-aware execution plan."""

    def build_execution_plan(
        self,
        *,
        handoff: dict[str, Any],
        reasoning_trace: dict[str, Any],
        session_id: str | None,
        run_id: str,
        task_id: str,
        normalized_input: str,
        control_routing: dict[str, Any] | None = None,
    ) -> tuple[ExecutionPlan, PlanningTrace]:
        routing = dict(control_routing or {})
        try:
            plan = self._synthesize(
                handoff=handoff,
                reasoning_trace=reasoning_trace,
                session_id=session_id,
                run_id=run_id,
                task_id=task_id,
                normalized_input=normalized_input,
                control_routing=routing,
            )
            trace_id = self._trace_id(session_id, run_id, plan.plan_id, degraded=False)
            trace = PlanningTrace.from_plan(plan, trace_id=trace_id, degraded=False, error="")
            return plan, trace
        except Exception as exc:
            plan = self._minimal_degraded_plan(
                handoff=handoff,
                reasoning_trace=reasoning_trace,
                session_id=session_id,
                run_id=run_id,
                task_id=task_id,
                normalized_input=normalized_input,
                error=str(exc),
            )
            trace_id = self._trace_id(session_id, run_id, plan.plan_id, degraded=True)
            trace = PlanningTrace.from_plan(plan, trace_id=trace_id, degraded=True, error=str(exc))
            return plan, trace

    @staticmethod
    def _trace_id(session_id: str | None, run_id: str, plan_id: str, *, degraded: bool) -> str:
        basis = f"{session_id}:{run_id}:{plan_id}:{'d' if degraded else 'n'}"
        digest = hashlib.sha1(basis.encode("utf-8")).hexdigest()[:16]
        return f"plan-{digest}"

    def _synthesize(
        self,
        *,
        handoff: dict[str, Any],
        reasoning_trace: dict[str, Any],
        session_id: str | None,
        run_id: str,
        task_id: str,
        normalized_input: str,
        control_routing: dict[str, Any],
    ) -> ExecutionPlan:
        plan_id = f"p33-plan-{uuid4().hex[:12]}"
        raw_steps = [str(s).strip() for s in (handoff.get("plan_steps") or []) if str(s).strip()]
        if not raw_steps:
            raw_steps = ["execute_primary_objective"]
        caps = [str(c).strip() for c in (handoff.get("suggested_capabilities") or []) if str(c).strip()]
        steps: list[ExecutionPlanStep] = []
        prev_id: str | None = None
        for idx, label in enumerate(raw_steps):
            sid = f"p33-step-{idx}-{_slug(label)}"
            depends = [prev_id] if prev_id else []
            stype = _STAGE_TO_STEP_TYPE.get(label, "execution")
            meta = {"reasoning_stage": label, "stage_index": idx}
            steps.append(
                ExecutionPlanStep(
                    step_id=sid,
                    step_type=stype,
                    summary=label.replace("_", " ").strip() or f"step_{idx}",
                    description=f"Derived from reasoning pipeline stage `{label}`.",
                    depends_on=depends,
                    requires_validation=label in {"validate", "risk_gate", "governance_confirmation"},
                    validation_checkpoint_id=None,
                    fallback_edge_id=None,
                    capability_hints=list(caps) if idx == len(raw_steps) - 1 else ([] if idx else list(caps[:3])),
                    metadata=meta,
                )
            )
            prev_id = sid

        checkpoints: list[PlanCheckpointBinding] = []
        cp_serial = 0
        for st in steps:
            if st.requires_validation:
                cp_serial += 1
                cp_id = f"{plan_id}-cp-{cp_serial}"
                checkpoints.append(
                    PlanCheckpointBinding(
                        checkpoint_id=cp_id,
                        label=f"post_{_slug(st.metadata['reasoning_stage'], 16)}",
                        after_step_id=st.step_id,
                        validation_kind="post_step_governance" if st.step_type == "governance" else "post_step",
                    )
                )
                st.validation_checkpoint_id = cp_id

        risk = str(control_routing.get("risk_level", "") or "").lower()
        verify = str(control_routing.get("verification_intensity", "") or "").lower()
        if (risk in {"high", "critical"} or verify == "high") and steps:
            last = steps[-1]
            if not any(c.after_step_id == last.step_id for c in checkpoints):
                cp_id = f"{plan_id}-cp-risk"
                checkpoints.append(
                    PlanCheckpointBinding(
                        checkpoint_id=cp_id,
                        label="pre_execution_control_checkpoint",
                        after_step_id=last.step_id,
                        validation_kind="control_routing",
                    )
                )

        fallbacks: list[PlanFallbackEdge] = []
        if len(steps) >= 2:
            fb_id = f"{plan_id}-fb-1"
            fallbacks.append(
                PlanFallbackEdge(
                    fallback_id=fb_id,
                    trigger_step_id=steps[-1].step_id,
                    target_step_id=steps[0].step_id,
                    notes="Bounded replan: retry from foundation step if terminal step fails validation.",
                )
            )
            steps[-1].fallback_edge_id = fb_id
        exec_strategy = str(handoff.get("execution_strategy", "") or "").lower()
        if exec_strategy == "guarded" and len(steps) >= 3:
            fb2 = f"{plan_id}-fb-guard"
            fallbacks.append(
                PlanFallbackEdge(
                    fallback_id=fb2,
                    trigger_step_id=steps[-2].step_id,
                    target_step_id=steps[1].step_id,
                    notes="Guarded strategy: partial rollback to staged checkpoint.",
                )
            )

        ready = bool(steps) and _topological_order_ok(steps)
        reasoning_tid = str(reasoning_trace.get("trace_id") or "").strip() or None
        title = f"Execution plan for {handoff.get('task_type', 'task')}"
        objective = str(handoff.get("reasoning_summary") or normalized_input).strip()[:400]
        summary = (
            f"{len(steps)} steps, {len(checkpoints)} checkpoints, {len(fallbacks)} fallback branches; "
            f"ready={ready}"
        )
        linked = {
            "reasoning_trace_id": reasoning_tid,
            "task_type": handoff.get("task_type"),
            "execution_strategy": handoff.get("execution_strategy"),
            "mode": handoff.get("mode"),
            "intent": handoff.get("intent"),
        }
        plan = ExecutionPlan(
            plan_id=plan_id,
            session_id=session_id,
            run_id=run_id or None,
            task_id=task_id,
            reasoning_trace_id=reasoning_tid,
            title=title,
            objective=objective,
            execution_ready=ready,
            planning_summary=summary,
            steps=steps,
            checkpoints=checkpoints,
            fallbacks=fallbacks,
            linked_reasoning=linked,
            metadata={
                "planning_engine_version": "33",
                "control_task_type": control_routing.get("task_type"),
                "control_risk_level": control_routing.get("risk_level"),
            },
            created_at=utc_now_iso(),
        )
        return plan

    def _minimal_degraded_plan(
        self,
        *,
        handoff: dict[str, Any],
        reasoning_trace: dict[str, Any],
        session_id: str | None,
        run_id: str,
        task_id: str,
        normalized_input: str,
        error: str,
    ) -> ExecutionPlan:
        plan_id = f"p33-plan-degraded-{uuid4().hex[:10]}"
        sid = f"{plan_id}-step-0"
        caps = [str(c).strip() for c in (handoff.get("suggested_capabilities") or []) if str(c).strip()][:5]
        step = ExecutionPlanStep(
            step_id=sid,
            step_type="execution",
            summary="stabilized_single_step_execution",
            description="Degraded plan: single safe execution step after planning synthesis error.",
            depends_on=[],
            requires_validation=True,
            validation_checkpoint_id=f"{plan_id}-cp-degraded",
            fallback_edge_id=None,
            capability_hints=caps,
            metadata={"degraded": True, "synthesis_error": error[:500]},
        )
        cp = PlanCheckpointBinding(
            checkpoint_id=f"{plan_id}-cp-degraded",
            label="post_planning_degraded_checkpoint",
            after_step_id=sid,
            validation_kind="degraded_path",
        )
        reasoning_tid = str(reasoning_trace.get("trace_id") or "").strip() or None
        return ExecutionPlan(
            plan_id=plan_id,
            session_id=session_id,
            run_id=run_id or None,
            task_id=task_id,
            reasoning_trace_id=reasoning_tid,
            title="Degraded execution plan",
            objective=str(normalized_input or handoff.get("intent", "")).strip()[:400],
            execution_ready=True,
            planning_summary="1 degraded step with mandatory checkpoint.",
            steps=[step],
            checkpoints=[cp],
            fallbacks=[],
            linked_reasoning={
                "reasoning_trace_id": reasoning_tid,
                "task_type": handoff.get("task_type"),
                "mode": handoff.get("mode"),
            },
            metadata={"planning_engine_version": "33", "degraded": True},
            created_at=utc_now_iso(),
        )
