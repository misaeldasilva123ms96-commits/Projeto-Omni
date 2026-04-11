from __future__ import annotations

from pathlib import Path
from typing import Any

from brain.runtime.patch_generator import build_patch

from .models import CauseHypothesis, FailureEvidence, RepairProposal, RepairValidationPlan


class DeterministicRepairProposer:
    def propose(
        self,
        *,
        workspace_root: Path,
        evidence: FailureEvidence,
        hypothesis: CauseHypothesis,
        allow_promotion: bool,
        advisory_signals: list[Any] | None = None,
    ) -> RepairProposal | None:
        strategy = hypothesis.repair_strategy_class
        if strategy == "ensure_file_content_contract":
            return self._propose_file_content_contract(
                workspace_root=workspace_root,
                evidence=evidence,
                hypothesis=hypothesis,
                allow_promotion=allow_promotion,
                advisory_signals=advisory_signals,
            )
        if strategy == "normalize_result_payload_shape":
            return self._propose_result_payload_normalizer(
                workspace_root=workspace_root,
                evidence=evidence,
                hypothesis=hypothesis,
                allow_promotion=allow_promotion,
                advisory_signals=advisory_signals,
            )
        if strategy == "normalize_error_payload_shape":
            return self._propose_error_payload_normalizer(
                workspace_root=workspace_root,
                evidence=evidence,
                hypothesis=hypothesis,
                allow_promotion=allow_promotion,
                advisory_signals=advisory_signals,
            )
        return None

    def _propose_file_content_contract(
        self,
        *,
        workspace_root: Path,
        evidence: FailureEvidence,
        hypothesis: CauseHypothesis,
        allow_promotion: bool,
        advisory_signals: list[Any] | None = None,
    ) -> RepairProposal | None:
        target_file = "backend/python/brain/runtime/engineering_tools.py"
        target_path = workspace_root / target_file
        if not target_path.exists():
            return None
        content = target_path.read_text(encoding="utf-8")
        anchor = 'return _ok(tool, {"file": {"filePath": str(target)}})'
        replacement = 'return _ok(tool, {"file": {"filePath": str(target), "content": content[:limit]}})'
        if anchor not in content:
            return None
        new_content = content.replace(anchor, replacement, 1)
        patch_payload = build_patch(
            workspace_root=workspace_root,
            file_path=target_file,
            new_content=new_content,
            confidence_score=hypothesis.confidence_score,
        )
        confidence = self._apply_learning_confidence(
            base_confidence=hypothesis.confidence_score,
            strategy=hypothesis.repair_strategy_class,
            evidence=evidence,
            advisory_signals=advisory_signals,
        )
        return RepairProposal.build(
            evidence_id=evidence.evidence_id,
            cause_category=hypothesis.probable_cause_category,
            repair_strategy_class=hypothesis.repair_strategy_class,
            target_file=target_file,
            proposed_action_summary="Restore the file.content contract for filesystem read results.",
            expected_fix_outcome="Read-oriented actions emit file.content so Phase 14 verification can pass.",
            scope_classification="single_file_runtime_patch",
            confidence_score=confidence,
            validation_plan=RepairValidationPlan(
                validation_modes=["patch-review", "source-compile", "import-load", "receipt-smoke"],
                targeted_tests=["tests.runtime.test_trusted_execution_layer"],
                require_import_validation=True,
                require_receipt_smoke_check=True,
                promotion_allowed=allow_promotion,
            ),
            promotion_conditions=[
                "Patch risk review passes",
                "Module import/load validation passes",
                "Trusted execution tests pass",
            ],
            patch_payload=patch_payload,
            metadata={"anchor": anchor, "replacement": replacement, "learning_signals": self._signal_ids(advisory_signals)},
        )

    def _propose_result_payload_normalizer(
        self,
        *,
        workspace_root: Path,
        evidence: FailureEvidence,
        hypothesis: CauseHypothesis,
        allow_promotion: bool,
        advisory_signals: list[Any] | None = None,
    ) -> RepairProposal | None:
        target_file = "backend/python/brain/runtime/execution/trusted_executor.py"
        target_path = workspace_root / target_file
        if not target_path.exists():
            return None
        content = target_path.read_text(encoding="utf-8")
        helper_anchor = "\n\nclass TrustedExecutor:"
        call_anchor = "            callback_result = execute_callback()"
        if helper_anchor not in content or call_anchor not in content:
            return None
        helper = (
            "\n\ndef _normalize_execution_callback_result(result: Any) -> dict[str, Any]:\n"
            "    if not isinstance(result, dict):\n"
            '        return {"ok": False, "error_payload": {"kind": "invalid_result_shape", "message": "Execution callback returned a non-dictionary result."}}\n'
            "    normalized = dict(result)\n"
            '    if normalized.get("ok") and "result_payload" not in normalized:\n'
            '        normalized["result_payload"] = {}\n'
            '    if not normalized.get("ok") and "error_payload" not in normalized:\n'
            '        normalized["error_payload"] = {"kind": "missing_error_payload", "message": "Execution callback failed without an error payload."}\n'
            "    return normalized\n"
        )
        if "_normalize_execution_callback_result" in content:
            return None
        new_content = content.replace(helper_anchor, helper_anchor.replace("\n\n", helper + "\n"), 1)
        new_content = new_content.replace(call_anchor, "            callback_result = _normalize_execution_callback_result(execute_callback())", 1)
        patch_payload = build_patch(
            workspace_root=workspace_root,
            file_path=target_file,
            new_content=new_content,
            confidence_score=hypothesis.confidence_score,
        )
        confidence = self._apply_learning_confidence(
            base_confidence=hypothesis.confidence_score,
            strategy=hypothesis.repair_strategy_class,
            evidence=evidence,
            advisory_signals=advisory_signals,
        )
        return RepairProposal.build(
            evidence_id=evidence.evidence_id,
            cause_category=hypothesis.probable_cause_category,
            repair_strategy_class=hypothesis.repair_strategy_class,
            target_file=target_file,
            proposed_action_summary="Normalize runtime callback results to ensure structured result payloads.",
            expected_fix_outcome="Execution wrappers always emit consistent result_payload and error_payload structures.",
            scope_classification="single_file_runtime_patch",
            confidence_score=confidence,
            validation_plan=RepairValidationPlan(
                validation_modes=["patch-review", "source-compile", "import-load", "receipt-smoke"],
                targeted_tests=["tests.runtime.test_trusted_execution_layer"],
                require_import_validation=True,
                require_receipt_smoke_check=True,
                promotion_allowed=allow_promotion,
            ),
            promotion_conditions=[
                "Patch risk review passes",
                "Trusted execution module imports cleanly",
                "Trusted execution tests pass",
            ],
            patch_payload=patch_payload,
            metadata={"target_component": hypothesis.affected_component, "learning_signals": self._signal_ids(advisory_signals)},
        )

    def _propose_error_payload_normalizer(
        self,
        *,
        workspace_root: Path,
        evidence: FailureEvidence,
        hypothesis: CauseHypothesis,
        allow_promotion: bool,
        advisory_signals: list[Any] | None = None,
    ) -> RepairProposal | None:
        target_file = "backend/python/brain/runtime/execution/trusted_executor.py"
        target_path = workspace_root / target_file
        if not target_path.exists():
            return None
        content = target_path.read_text(encoding="utf-8")
        old_line = '                    "kind": "execution_exception",\n                    "message": str(exc),\n'
        new_line = (
            '                    "kind": "execution_exception",\n'
            '                    "message": str(exc),\n'
            '                    "details": {"exception_type": type(exc).__name__},\n'
        )
        if old_line not in content:
            return None
        new_content = content.replace(old_line, new_line, 1)
        patch_payload = build_patch(
            workspace_root=workspace_root,
            file_path=target_file,
            new_content=new_content,
            confidence_score=hypothesis.confidence_score,
        )
        confidence = self._apply_learning_confidence(
            base_confidence=hypothesis.confidence_score,
            strategy=hypothesis.repair_strategy_class,
            evidence=evidence,
            advisory_signals=advisory_signals,
        )
        return RepairProposal.build(
            evidence_id=evidence.evidence_id,
            cause_category=hypothesis.probable_cause_category,
            repair_strategy_class=hypothesis.repair_strategy_class,
            target_file=target_file,
            proposed_action_summary="Normalize exception failures so structured error details are always preserved.",
            expected_fix_outcome="Failed execution paths emit complete structured error payloads.",
            scope_classification="single_file_runtime_patch",
            confidence_score=confidence,
            validation_plan=RepairValidationPlan(
                validation_modes=["patch-review", "source-compile", "import-load", "receipt-smoke"],
                targeted_tests=["tests.runtime.test_trusted_execution_layer"],
                require_import_validation=True,
                require_receipt_smoke_check=True,
                promotion_allowed=allow_promotion,
            ),
            promotion_conditions=[
                "Patch risk review passes",
                "Execution module imports cleanly",
                "Trusted execution tests pass",
            ],
            patch_payload=patch_payload,
            metadata={"target_component": hypothesis.affected_component, "learning_signals": self._signal_ids(advisory_signals)},
        )

    @staticmethod
    def _signal_ids(advisory_signals: list[Any] | None) -> list[str]:
        return [str(getattr(signal, "signal_id", "")) for signal in advisory_signals or [] if str(getattr(signal, "signal_id", ""))]

    @staticmethod
    def _apply_learning_confidence(
        *,
        base_confidence: float,
        strategy: str,
        evidence: FailureEvidence,
        advisory_signals: list[Any] | None,
    ) -> float:
        confidence = base_confidence
        for signal in advisory_signals or []:
            signal_type = getattr(getattr(signal, "signal_type", None), "value", "")
            metadata = getattr(signal, "metadata", {}) if isinstance(getattr(signal, "metadata", {}), dict) else {}
            if signal_type != "preferred_repair_strategy":
                continue
            if str(metadata.get("repair_strategy", "")).strip() not in {"", strategy}:
                continue
            if str(metadata.get("failure_class", "")).strip() not in {"", evidence.failure_type}:
                continue
            confidence = min(0.99, confidence + float(getattr(signal, "weight", 0.0) or 0.0) * 0.2)
        return confidence
