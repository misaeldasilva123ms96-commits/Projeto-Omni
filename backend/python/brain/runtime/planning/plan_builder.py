from __future__ import annotations

import hashlib
from typing import Any

from .models import PlanStep, PlanStepStatus, TaskClassification, TaskPlan


class OperationalPlanBuilder:
    def build_plan(
        self,
        *,
        task_id: str,
        session_id: str,
        run_id: str,
        message: str,
        actions: list[dict[str, Any]],
        classification: TaskClassification,
        plan_kind: str = "linear",
        advisory_signals: list[dict[str, Any]] | None = None,
    ) -> TaskPlan:
        objective = str(message or "Execute runtime workflow.").strip() or "Execute runtime workflow."
        title = objective[:96]
        steps: list[PlanStep] = []
        previous_dependencies: list[str] = []
        validation_tools = self._validation_tools_from_signals(advisory_signals)

        if classification in {
            TaskClassification.MULTI_STEP,
            TaskClassification.RESUMABLE_WORKFLOW,
            TaskClassification.LONG_RUNNING_WORK,
        }:
            inspect_step = PlanStep(
                step_id="inspect_context",
                title="Inspect Context",
                description="Prepare runtime context, dependencies, and execution boundaries before operational steps begin.",
                step_type="inspect_context",
                dependency_step_ids=[],
                status=PlanStepStatus.PENDING,
                expected_outcome="Execution context is ready and auditable.",
                metadata={"auto_managed": True, "plan_kind": plan_kind},
            )
            steps.append(inspect_step)
            previous_dependencies = [inspect_step.step_id]

        action_step_ids: list[str] = []
        for index, action in enumerate(actions, start=1):
            action_step_id = str(action.get("step_id", "") or f"runtime-step-{index}")
            dependency_step_ids = [
                f"action:{str(item).strip()}"
                for item in (action.get("depends_on_step_ids") or action.get("depends_on") or [])
                if str(item).strip()
            ]
            if not dependency_step_ids and previous_dependencies:
                dependency_step_ids = list(previous_dependencies)
            action_step = PlanStep(
                step_id=f"action:{action_step_id}",
                title=str(action.get("title") or action.get("description") or f"Execute {action.get('selected_tool', 'runtime action')}").strip(),
                description=str(action.get("description") or f"Execute runtime action {action_step_id}.").strip(),
                step_type="execute_action",
                dependency_step_ids=dependency_step_ids,
                status=PlanStepStatus.PENDING,
                expected_outcome=str(action.get("expected_outcome") or f"{action.get('selected_tool', 'runtime action')} completes with a coherent result."),
                metadata={
                    "action_step_id": action_step_id,
                    "selected_tool": str(action.get("selected_tool", "")),
                    "selected_agent": str(action.get("selected_agent", "")),
                    "action_signature": hashlib.sha1(str(action).encode("utf-8")).hexdigest()[:16],
                },
            )
            steps.append(action_step)
            action_step_ids.append(action_step.step_id)
            previous_dependencies = [action_step.step_id]
            selected_tool = str(action.get("selected_tool", "")).strip()
            if selected_tool and selected_tool in validation_tools:
                validation_step = PlanStep(
                    step_id=f"validate:{action_step_id}",
                    title=f"Validate {selected_tool}",
                    description=f"Run a bounded validation checkpoint after {selected_tool} because learned evidence indicates this step benefits from explicit validation.",
                    step_type="validate_result",
                    dependency_step_ids=[action_step.step_id],
                    status=PlanStepStatus.PENDING,
                    expected_outcome=f"{selected_tool} outcome is validated before the workflow continues.",
                    metadata={
                        "auto_managed": True,
                        "selected_tool": selected_tool,
                        "learning_advisory": True,
                    },
                )
                steps.append(validation_step)
                previous_dependencies = [validation_step.step_id]

        summarize_dependencies = action_step_ids or previous_dependencies
        summarize_step = PlanStep(
            step_id="summarize_outcome",
            title="Summarize Outcome",
            description="Consolidate the operational outcome, latest state, and next action recommendation.",
            step_type="summarize_outcome",
            dependency_step_ids=summarize_dependencies,
            status=PlanStepStatus.PENDING,
            expected_outcome="Operational summary is available for continuity across turns.",
            metadata={"auto_managed": True},
        )
        steps.append(summarize_step)

        checkpoint_step = PlanStep(
            step_id="persist_checkpoint",
            title="Persist Checkpoint",
            description="Persist the latest resumable state after operational execution settles.",
            step_type="persist_checkpoint",
            dependency_step_ids=[summarize_step.step_id],
            status=PlanStepStatus.PENDING,
            expected_outcome="A compact resumable checkpoint is persisted for the task.",
            metadata={"auto_managed": True},
        )
        steps.append(checkpoint_step)

        return TaskPlan.build(
            task_id=task_id,
            title=title,
            objective=objective,
            classification=classification,
            steps=steps,
            session_id=session_id,
            run_id=run_id,
            metadata={
                "message": objective,
                "plan_kind": plan_kind,
                "action_count": len(actions),
                "action_step_ids": action_step_ids,
                "advisory_signal_count": len(advisory_signals or []),
            },
        )

    @staticmethod
    def _validation_tools_from_signals(advisory_signals: list[dict[str, Any]] | None) -> set[str]:
        tools: set[str] = set()
        for signal in advisory_signals or []:
            if not isinstance(signal, dict):
                continue
            if str(signal.get("signal_type", "")).strip() != "step_template_success_hint":
                continue
            metadata = signal.get("metadata", {}) if isinstance(signal.get("metadata"), dict) else {}
            if not metadata.get("require_validation_after_tool"):
                continue
            selected_tool = str(metadata.get("selected_tool", "")).strip()
            if selected_tool:
                tools.add(selected_tool)
        return tools
