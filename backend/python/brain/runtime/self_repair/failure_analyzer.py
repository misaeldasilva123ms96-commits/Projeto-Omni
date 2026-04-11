from __future__ import annotations

from typing import Any

from .models import CauseHypothesis, FailureEvidence


class FailureAnalyzer:
    def build_evidence(
        self,
        *,
        action: dict[str, Any],
        result: dict[str, Any],
        trusted_execution: Any | None,
        retry_count: int,
        recurrence_count: int,
    ) -> FailureEvidence:
        error_payload = result.get("error_payload", {}) if isinstance(result.get("error_payload"), dict) else {}
        trusted_payload = result.get("trusted_execution", {}) if isinstance(result.get("trusted_execution"), dict) else {}
        verification_payload = trusted_payload.get("verification", {}) if isinstance(trusted_payload.get("verification"), dict) else {}
        execution_receipt = result.get("execution_receipt", {}) if isinstance(result.get("execution_receipt"), dict) else {}
        linked_receipt_ids: list[str] = []
        receipt_id = execution_receipt.get("receipt_id")
        if isinstance(receipt_id, str) and receipt_id.strip():
            linked_receipt_ids.append(receipt_id.strip())

        selected_tool = str(action.get("selected_tool", "")).strip()
        action_type = str(action.get("action_type", "execute") or "execute")
        subsystem = str(action.get("target_subsystem", "")).strip()
        if not subsystem:
            subsystem = "engineering_tools" if selected_tool in {"filesystem_read", "filesystem_write", "filesystem_patch_set", "verification_runner", "test_runner"} else "runtime_execution"

        return FailureEvidence.build(
            action_id=str(action.get("step_id", "") or action.get("action_id", selected_tool or "runtime-action")),
            action_type=action_type,
            subsystem=subsystem,
            failure_type=str(error_payload.get("kind", "execution_failed") or "execution_failed"),
            failure_message_summary=str(error_payload.get("message", "Execution failed.")),
            error_details=error_payload,
            verification_details=verification_payload,
            retry_count=retry_count,
            recurrence_count=recurrence_count,
            session_id=str(action.get("session_id", "") or "") or None,
            task_id=str(action.get("task_id", "") or "") or None,
            run_id=str(action.get("run_id", "") or "") or None,
            source_receipt_id=str(receipt_id) if isinstance(receipt_id, str) and receipt_id.strip() else None,
            linked_execution_receipt_ids=linked_receipt_ids,
            capability=selected_tool,
            selected_agent=str(action.get("selected_agent", "")),
            source_result_snapshot={
                "ok": result.get("ok"),
                "selected_tool": result.get("selected_tool"),
                "selected_agent": result.get("selected_agent"),
                "error_payload": error_payload,
                "trusted_execution": trusted_payload,
            },
            metadata={
                "missing_fields": list(verification_payload.get("missing_fields", []) or []),
                "verification_reason_code": verification_payload.get("reason_code"),
            },
        )

    def analyze(self, evidence: FailureEvidence) -> CauseHypothesis:
        missing_fields = list(evidence.verification_details.get("missing_fields", []) or [])
        failure_type = str(evidence.failure_type)
        capability = str(evidence.capability)

        if failure_type == "verification_failed" and "file.content" in missing_fields:
            return CauseHypothesis(
                probable_cause_category="result_contract_mismatch",
                confidence_score=0.92,
                affected_component="engineering_tools",
                repair_strategy_class="ensure_file_content_contract",
                rationale="The trusted verifier reported a missing file.content field for a read-oriented action.",
            )

        if failure_type in {"missing_result_payload", "invalid_result_shape"}:
            return CauseHypothesis(
                probable_cause_category="result_shape_mismatch",
                confidence_score=0.84,
                affected_component="execution_wrapper",
                repair_strategy_class="normalize_result_payload_shape",
                rationale="The failure indicates that a structured result payload was missing or malformed.",
            )

        if failure_type == "missing_error_payload":
            return CauseHypothesis(
                probable_cause_category="error_shape_mismatch",
                confidence_score=0.81,
                affected_component="execution_wrapper",
                repair_strategy_class="normalize_error_payload_shape",
                rationale="The failure indicates that an error path did not emit a structured error payload.",
            )

        if evidence.recurrence_count > 1 and failure_type in {"execution_exception", "verification_failed"}:
            return CauseHypothesis(
                probable_cause_category="repeated_deterministic_failure",
                confidence_score=0.7,
                affected_component="execution_wrapper",
                repair_strategy_class="normalize_result_payload_shape",
                rationale="Repeated failures of the same deterministic action suggest a bounded adapter defect.",
            )

        return CauseHypothesis(
            probable_cause_category="unknown_failure_pattern",
            confidence_score=0.2,
            affected_component="unknown",
            repair_strategy_class="no_repair_strategy",
            rationale=f"No deterministic repair hypothesis was found for {failure_type or capability or 'unknown failure'}.",
        )
