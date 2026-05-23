from __future__ import annotations

import re
import uuid
from typing import Any

from .decomposition_limits import MAX_BRANCHES_PER_NODE, MAX_DEPTH, MAX_SUBTASKS
from .decomposition_models import DecompositionResult, DecompositionTrace, SubTask
from .decomposition_rules import should_include_generation, strategy_mode


def _slug(s: str, max_len: int = 32) -> str:
    t = re.sub(r"[^a-zA-Z0-9_-]+", "-", str(s or "").strip())[:max_len].strip("-")
    return t or "step"


class TaskDecomposer:
    """Phase 38 — bounded decomposition from ExecutionPlan (+ reasoning/strategy context)."""

    def decompose(
        self,
        *,
        execution_plan: dict[str, Any],
        reasoning_trace: dict[str, Any],
        strategy_summary: dict[str, Any],
        coordination_hint: dict[str, Any] | None = None,
        tuning_overrides: dict[str, Any] | None = None,
    ) -> DecompositionResult:
        """
        Produces structured subtasks linked to plan steps only (no recursive re-planning).
        coordination_hint reserved for future bounded hints from Phase 37 state; must not execute work.
        """
        _ = coordination_hint
        eff_max = MAX_SUBTASKS
        if isinstance(tuning_overrides, dict):
            try:
                raw_m = int(tuning_overrides.get("decomposition_max_subtasks", eff_max) or eff_max)
                eff_max = max(4, min(8, raw_m))
            except (TypeError, ValueError):
                eff_max = MAX_SUBTASKS
        plan_id = str(execution_plan.get("plan_id", "") or "").strip()
        reasoning_link = str(reasoning_trace.get("trace_id", "") or "").strip()
        st_link = ""
        if isinstance(strategy_summary.get("strategy_trace"), dict):
            st_link = str(strategy_summary["strategy_trace"].get("trace_id", "") or "").strip()

        steps = execution_plan.get("steps") if isinstance(execution_plan.get("steps"), list) else []
        mode = strategy_mode(strategy_summary if isinstance(strategy_summary, dict) else {})
        subtasks: list[SubTask] = []
        warnings: list[str] = []
        max_depth_observed = 0
        max_depth_reached = False
        truncated = False

        parent_ids = {str(s.get("step_id", "")).strip() for s in steps if isinstance(s, dict) and str(s.get("step_id", "")).strip()}

        for step in steps:
            if not isinstance(step, dict):
                continue
            if len(subtasks) >= eff_max:
                truncated = True
                warnings.append("truncated_max_subtasks")
                break
            sid = str(step.get("step_id", "")).strip() or _slug(str(step.get("summary", "step")))
            summary = str(step.get("summary", "") or step.get("description", "") or "").strip()[:400]
            branches: list[tuple[str, str]] = []

            branches.append(
                (
                    "analysis",
                    f"Clarify inputs and success criteria for plan step {sid}: {summary or 'n/a'}",
                )
            )
            if should_include_generation(step, mode):
                branches.append(
                    (
                        "generation",
                        f"Produce or modify artifacts required by step {sid}: {summary or 'n/a'}",
                    )
                )
            if bool(step.get("requires_validation")):
                branches.append(
                    (
                        "validation",
                        f"Validate outcomes and constraints after step {sid}.",
                    )
                )
            branches.append(
                (
                    "execution",
                    f"Execute primary work for plan step {sid}: {summary or 'n/a'}",
                )
            )

            emitted_for_step = 0
            last_analysis_id: str | None = None
            for kind, desc in branches:
                if emitted_for_step >= MAX_BRANCHES_PER_NODE:
                    if len(branches) > emitted_for_step:
                        truncated = True
                        warnings.append("truncated_max_branches_per_node")
                    break
                if len(subtasks) >= eff_max:
                    truncated = True
                    warnings.append("truncated_max_subtasks")
                    break
                stid = f"{_slug(plan_id, 12)}-{sid}-{_slug(kind, 12)}-{uuid.uuid4().hex[:6]}"
                depth = 1
                max_depth_observed = max(max_depth_observed, depth)
                if depth >= MAX_DEPTH:
                    max_depth_reached = True
                depends: list[str] = []
                if kind in ("generation", "execution", "validation") and last_analysis_id:
                    depends = [last_analysis_id]
                subtasks.append(
                    SubTask(
                        id=stid,
                        description=desc[:800],
                        parent_step_id=sid,
                        depends_on=depends,
                        type=kind,
                        depth=depth,
                    )
                )
                if kind == "analysis":
                    last_analysis_id = stid
                emitted_for_step += 1

        tw = list(warnings)
        if not plan_id:
            tw.append("missing_plan_id")
        if not parent_ids:
            tw.append("no_plan_steps")

        trace_id = f"dec38-{uuid.uuid4().hex[:18]}"
        trace = DecompositionTrace(
            trace_id=trace_id,
            plan_id=plan_id,
            reasoning_link=reasoning_link,
            subtask_count=len(subtasks),
            max_depth_observed=max_depth_observed,
            truncated=truncated,
            max_depth_reached=max_depth_reached,
            warnings=tw,
            strategy_trace_link=st_link,
        )

        return DecompositionResult(subtasks=subtasks, trace=trace)
