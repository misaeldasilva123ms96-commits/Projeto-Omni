from __future__ import annotations

from typing import Any, Callable


ConstraintCallable = Callable[[Any, dict[str, Any]], tuple[bool, str]]


class ConstraintRegistry:
    def __init__(self) -> None:
        self._registry: dict[str, ConstraintCallable] = {}
        self._register_defaults()

    def register(self, name: str, evaluator: ConstraintCallable) -> None:
        self._registry[str(name).strip()] = evaluator

    def get(self, name: str) -> ConstraintCallable | None:
        return self._registry.get(str(name).strip())

    def evaluate(self, name: str, item: Any, runtime_state: dict[str, Any] | None = None) -> tuple[bool, str]:
        evaluator = self.get(name)
        if evaluator is None:
            return False, f"Missing evaluator: {name}"
        try:
            return evaluator(item, runtime_state or {})
        except Exception as error:
            return False, f"Evaluator {name} failed: {error}"

    def _register_defaults(self) -> None:
        self.register("always_true", lambda item, state: (True, "Default evaluator passed."))
        self.register(
            "result_ok",
            lambda item, state: (
                bool(state.get("result_ok")) or bool((state.get("result") or {}).get("ok")),
                "Execution result indicates success."
                if bool(state.get("result_ok")) or bool((state.get("result") or {}).get("ok"))
                else "Execution result is not successful.",
            ),
        )
        self.register(
            "successful_steps_exist",
            lambda item, state: (
                int(state.get("successful_steps", state.get("successful_steps_count", 0)) or 0) > 0,
                "At least one successful step exists."
                if int(state.get("successful_steps", state.get("successful_steps_count", 0)) or 0) > 0
                else "No successful steps recorded.",
            ),
        )
        self.register(
            "goal_plan_complete",
            lambda item, state: (
                float(state.get("partial_success", 0.0) or 0.0) >= float((getattr(item, "metadata", {}) or {}).get("required_progress", 1.0) or 1.0)
                or str(state.get("summary_status", "")).strip() == "completed",
                "Plan progress satisfies the inferred goal completion threshold."
                if float(state.get("partial_success", 0.0) or 0.0) >= float((getattr(item, "metadata", {}) or {}).get("required_progress", 1.0) or 1.0)
                or str(state.get("summary_status", "")).strip() == "completed"
                else "Plan progress has not yet satisfied the inferred goal completion threshold.",
            ),
        )
        self.register(
            "proposal_within_goal_scope",
            lambda item, state: (
                str(state.get("proposal_target_subsystem", "")).strip() in set((getattr(item, "metadata", {}) or {}).get("allowed_subsystems", []))
                if (getattr(item, "metadata", {}) or {}).get("allowed_subsystems")
                else True,
                "Proposal stays within allowed goal subsystems."
                if str(state.get("proposal_target_subsystem", "")).strip() in set((getattr(item, "metadata", {}) or {}).get("allowed_subsystems", []))
                or not (getattr(item, "metadata", {}) or {}).get("allowed_subsystems")
                else "Proposal target subsystem violates goal scope.",
            ),
        )
        self.register(
            "max_cycles_not_reached",
            lambda item, state: (
                int(state.get("cycle_count", 0) or 0) < int((getattr(item, "metadata", {}) or {}).get("max_cycles", getattr(item, "threshold", 0)) or 0),
                "Cycle limit not reached."
                if int(state.get("cycle_count", 0) or 0) < int((getattr(item, "metadata", {}) or {}).get("max_cycles", getattr(item, "threshold", 0)) or 0)
                else "Cycle limit reached.",
            ),
        )
        self.register(
            "timeout_not_reached",
            lambda item, state: (
                float(state.get("elapsed_seconds", 0.0) or 0.0) < float((getattr(item, "metadata", {}) or {}).get("timeout_seconds", getattr(item, "threshold", 0.0)) or 0.0),
                "Timeout not reached."
                if float(state.get("elapsed_seconds", 0.0) or 0.0) < float((getattr(item, "metadata", {}) or {}).get("timeout_seconds", getattr(item, "threshold", 0.0)) or 0.0)
                else "Timeout reached.",
            ),
        )
        self.register(
            "dependency_not_failed",
            lambda item, state: (not bool(state.get("dependency_failed")), "Dependencies remain healthy." if not bool(state.get("dependency_failed")) else "A dependency has failed."),
        )
