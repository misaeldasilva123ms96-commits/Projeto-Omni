from __future__ import annotations

from typing import Any

from .models import LearningEvidence, LearningSourceType


class EvidenceNormalizer:
    def normalize(
        self,
        *,
        source_type: LearningSourceType,
        payload: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> LearningEvidence | None:
        context = context or {}
        if source_type == LearningSourceType.EXECUTION_RECEIPT:
            return self._from_execution_receipt(payload, context)
        if source_type == LearningSourceType.REPAIR_RECEIPT:
            return self._from_repair_receipt(payload, context)
        if source_type == LearningSourceType.PLAN_CHECKPOINT:
            return self._from_plan_checkpoint(payload, context)
        if source_type == LearningSourceType.OPERATIONAL_SUMMARY:
            return self._from_operational_summary(payload, context)
        if source_type == LearningSourceType.CONTINUATION_DECISION:
            return self._from_continuation_decision(payload, context)
        if source_type == LearningSourceType.CONTINUATION_EVALUATION:
            return self._from_continuation_evaluation(payload, context)
        return None

    @staticmethod
    def _common_context(payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        action = context.get("action", {}) if isinstance(context.get("action"), dict) else {}
        return {
            "session_id": str(payload.get("session_id") or context.get("session_id") or action.get("session_id") or "") or None,
            "task_id": str(payload.get("task_id") or context.get("task_id") or action.get("task_id") or "") or None,
            "goal_id": str(payload.get("goal_id") or context.get("goal_id") or action.get("goal_id") or "") or None,
            "plan_id": str(payload.get("plan_id") or context.get("plan_id") or "") or None,
            "step_id": str(payload.get("step_id") or action.get("step_id") or "") or None,
            "action_type": str(payload.get("action_type") or action.get("action_type") or "execute"),
            "capability": str(payload.get("capability") or action.get("selected_tool") or ""),
            "subsystem": str(payload.get("subsystem") or action.get("target_subsystem") or "python-runtime"),
        }

    def _from_execution_receipt(self, payload: dict[str, Any], context: dict[str, Any]) -> LearningEvidence | None:
        artifact_id = str(payload.get("receipt_id", "")).strip()
        if not artifact_id:
            return None
        common = self._common_context(payload, context)
        execution_status = str(payload.get("execution_status", "")).strip()
        verification_status = str(payload.get("verification_status", "")).strip()
        success = execution_status == "succeeded" and verification_status == "passed"
        outcome_class = "execution_verified" if success else "verification_failed" if verification_status == "failed" else "execution_failed"
        error_details = payload.get("error_details", {}) if isinstance(payload.get("error_details"), dict) else {}
        failure_class = str(error_details.get("kind", "")).strip() or outcome_class
        return LearningEvidence.build(
            source_type=LearningSourceType.EXECUTION_RECEIPT,
            source_artifact_id=artifact_id,
            session_id=common["session_id"],
            task_id=common["task_id"],
            goal_id=common["goal_id"],
            plan_id=common["plan_id"],
            step_id=common["step_id"],
            action_type=common["action_type"],
            capability=common["capability"],
            subsystem=common["subsystem"],
            outcome_class=outcome_class,
            success=success,
            failure_class=failure_class if not success else "",
            retry_count=int(payload.get("retry_count", 0) or 0),
            timestamp=str(payload.get("timestamp", "")),
            metadata=dict(payload.get("metadata", {}) or {}),
        )

    def _from_repair_receipt(self, payload: dict[str, Any], context: dict[str, Any]) -> LearningEvidence | None:
        artifact_id = str(payload.get("repair_receipt_id", "")).strip()
        if not artifact_id:
            return None
        action = context.get("action", {}) if isinstance(context.get("action"), dict) else {}
        promotion_status = str(payload.get("promotion_status", "")).strip()
        success = promotion_status in {"promoted", "validated"}
        return LearningEvidence.build(
            source_type=LearningSourceType.REPAIR_RECEIPT,
            source_artifact_id=artifact_id,
            session_id=str(context.get("session_id") or action.get("session_id") or "") or None,
            task_id=str(context.get("task_id") or action.get("task_id") or "") or None,
            goal_id=str(context.get("goal_id") or action.get("goal_id") or "") or None,
            plan_id=str(context.get("plan_id") or "") or None,
            step_id=str(action.get("step_id", "")) or None,
            action_type=str(action.get("action_type", "repair")),
            capability=str(action.get("selected_tool", "")),
            subsystem="self_repair",
            outcome_class=f"repair_{promotion_status or 'rejected'}",
            success=success,
            failure_class=str(payload.get("rejection_reason", "")).strip() if not success else "",
            retry_count=int(payload.get("attempt_count", 0) or 0),
            repair_attempted=True,
            repair_promoted=promotion_status == "promoted",
            timestamp=str(payload.get("timestamp", "")),
            metadata={
                "repair_strategy": str(payload.get("repair_strategy", "")),
                "cause_category": str(payload.get("cause_category", "")),
                "proposal_id": str(payload.get("proposal_id", "")),
                "linked_execution_receipt_ids": list(payload.get("linked_execution_receipt_ids", []) or []),
            },
        )

    def _from_plan_checkpoint(self, payload: dict[str, Any], context: dict[str, Any]) -> LearningEvidence | None:
        artifact_id = str(payload.get("checkpoint_id", "")).strip()
        if not artifact_id:
            return None
        resumable_state = payload.get("resumable_state_payload", {}) if isinstance(payload.get("resumable_state_payload"), dict) else {}
        status = str(payload.get("status", "")).strip()
        resume_decision = str(resumable_state.get("resume_decision", "")).strip()
        outcome_class = "resume_checkpoint" if resume_decision else f"checkpoint_{status or 'valid'}"
        return LearningEvidence.build(
            source_type=LearningSourceType.PLAN_CHECKPOINT,
            source_artifact_id=artifact_id,
            session_id=str(context.get("session_id") or "") or None,
            task_id=str(context.get("task_id") or "") or None,
            goal_id=str(context.get("goal_id") or "") or None,
            plan_id=str(payload.get("plan_id", "") or context.get("plan_id") or "") or None,
            step_id=str(payload.get("step_id", "")) or None,
            action_type="checkpoint",
            capability="checkpoint_manager",
            subsystem="planning",
            outcome_class=outcome_class,
            success=status != "invalid",
            failure_class="checkpoint_invalid" if status == "invalid" else "",
            timestamp=str(payload.get("timestamp", "")),
            metadata={"resumable_state": resumable_state, "snapshot_summary": str(payload.get("snapshot_summary", ""))},
        )

    def _from_operational_summary(self, payload: dict[str, Any], context: dict[str, Any]) -> LearningEvidence | None:
        plan_id = str(payload.get("plan_id", "")).strip()
        if not plan_id:
            return None
        plan_status = str(payload.get("plan_status", "")).strip()
        return LearningEvidence.build(
            source_type=LearningSourceType.OPERATIONAL_SUMMARY,
            source_artifact_id=plan_id,
            session_id=str(context.get("session_id") or "") or None,
            task_id=str(payload.get("task_id", "") or context.get("task_id") or "") or None,
            goal_id=str(payload.get("goal_id", "") or context.get("goal_id") or "") or None,
            plan_id=plan_id,
            step_id=str(payload.get("current_step", "")) or None,
            action_type="plan_summary",
            capability="planning_summary",
            subsystem="planning",
            outcome_class=f"plan_{plan_status or 'unknown'}",
            success=plan_status in {"completed", "active", "paused"},
            failure_class="plan_blocked" if plan_status in {"blocked", "failed"} else "",
            metadata={
                "next_recommended_action": str(payload.get("next_recommended_action", "")),
                "resumability_state": str(payload.get("resumability_state", "")),
                "goal_description": str(context.get("goal_description", "")),
            },
        )

    def _from_continuation_decision(self, payload: dict[str, Any], context: dict[str, Any]) -> LearningEvidence | None:
        artifact_id = str(payload.get("decision_id", "")).strip()
        if not artifact_id:
            return None
        decision_type = str(payload.get("decision_type", "")).strip()
        return LearningEvidence.build(
            source_type=LearningSourceType.CONTINUATION_DECISION,
            source_artifact_id=artifact_id,
            session_id=str(context.get("session_id") or "") or None,
            task_id=str(payload.get("task_id", "") or context.get("task_id") or "") or None,
            goal_id=str(payload.get("goal_id", "") or context.get("goal_id") or "") or None,
            plan_id=str(payload.get("plan_id", "") or context.get("plan_id") or "") or None,
            step_id=str(payload.get("step_id", "")) or None,
            action_type="continuation",
            capability="continuation_decider",
            subsystem="continuation",
            outcome_class=f"continuation_{decision_type or 'unknown'}",
            success=decision_type in {"continue_execution", "complete_plan", "pause_plan"},
            failure_class="escalated_continuation" if decision_type == "escalate_failure" else "",
            continuation_decision_type=decision_type,
            timestamp=str(payload.get("timestamp", "")),
            metadata={
                "decision_type": decision_type,
                "linked_execution_receipt_ids": list(payload.get("linked_execution_receipt_ids", []) or []),
                "linked_repair_receipt_ids": list(payload.get("linked_repair_receipt_ids", []) or []),
            },
        )

    def _from_continuation_evaluation(self, payload: dict[str, Any], context: dict[str, Any]) -> LearningEvidence | None:
        artifact_id = str(payload.get("evaluation_id", "")).strip()
        if not artifact_id:
            return None
        plan_health = str(payload.get("plan_health", "")).strip()
        repair_summary = str(payload.get("repair_outcome_summary", "")).strip()
        return LearningEvidence.build(
            source_type=LearningSourceType.CONTINUATION_EVALUATION,
            source_artifact_id=artifact_id,
            session_id=str(context.get("session_id") or "") or None,
            task_id=str(context.get("task_id") or "") or None,
            goal_id=str(context.get("goal_id") or "") or None,
            plan_id=str(payload.get("plan_id", "") or context.get("plan_id") or "") or None,
            step_id=str(payload.get("current_step_id", "")) or None,
            action_type="continuation_evaluation",
            capability="plan_evaluator",
            subsystem="continuation",
            outcome_class=f"plan_health_{plan_health or 'unknown'}",
            success=plan_health in {"healthy", "completed"},
            failure_class="plan_blocked" if plan_health == "blocked" else "",
            retry_count=int(round(float(payload.get("retry_pressure", 0.0) or 0.0))),
            repair_attempted=repair_summary.startswith(("rejected", "promoted", "validated")),
            repair_promoted=repair_summary.startswith("promoted"),
            timestamp=str(payload.get("timestamp", "")),
            metadata={
                "plan_health": plan_health,
                "dependency_health": str(payload.get("dependency_health", "")),
                "resumability_state": str(payload.get("resumability_state", "")),
            },
        )
