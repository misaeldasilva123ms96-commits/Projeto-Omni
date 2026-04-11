from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from uuid import uuid4

from brain.runtime.patch_generator import apply_patch, review_patch_risk, rollback_patch

from .models import FailureEvidence, RepairProposal, RepairValidationResult, SelfRepairPolicy


class RepairValidator:
    def validate(
        self,
        *,
        workspace_root: Path,
        proposal: RepairProposal,
        evidence: FailureEvidence,
        policy: SelfRepairPolicy,
    ) -> RepairValidationResult:
        patch_payload = dict(proposal.patch_payload or {})
        validated_items: list[str] = []
        review = review_patch_risk(patch=patch_payload)
        if not review.get("accepted"):
            return RepairValidationResult(
                passed=False,
                validated_items=["patch-review"],
                error_output_summary=f"Patch risk review rejected repair: {', '.join(review.get('warnings', []))}",
                confidence_adjustment=-0.3,
                promotion_allowed=False,
            )
        validated_items.append("patch-review")

        try:
            compile(str(patch_payload.get("new_content", "")), proposal.target_file, "exec")
        except Exception as error:
            return RepairValidationResult(
                passed=False,
                validated_items=validated_items + ["source-compile"],
                error_output_summary=f"Source compile validation failed: {error}",
                confidence_adjustment=-0.4,
                promotion_allowed=False,
            )
        validated_items.append("source-compile")

        smoke_ok, smoke_message = self._receipt_smoke_check(proposal=proposal)
        if not smoke_ok:
            return RepairValidationResult(
                passed=False,
                validated_items=validated_items + ["receipt-smoke"],
                error_output_summary=smoke_message,
                confidence_adjustment=-0.2,
                promotion_allowed=False,
            )
        validated_items.append("receipt-smoke")

        if not policy.allow_promotion:
            import_ok, import_message = self._run_import_validation(
                workspace_root=workspace_root,
                target_file=proposal.target_file,
                candidate_content=str(patch_payload.get("new_content", "")),
            )
            if not import_ok:
                return RepairValidationResult(
                    passed=False,
                    validated_items=validated_items + ["import-load"],
                    error_output_summary=import_message,
                    confidence_adjustment=-0.25,
                    promotion_allowed=False,
                )
            return RepairValidationResult(
                passed=True,
                validated_items=validated_items + ["import-load"],
                error_output_summary="Promotion disabled by policy; validation passed without applying the patch.",
                confidence_adjustment=0.1,
                promotion_allowed=False,
            )

        apply_result = apply_patch(workspace_root=workspace_root, patch=patch_payload)
        if not apply_result.get("ok"):
            return RepairValidationResult(
                passed=False,
                validated_items=validated_items + ["patch-apply"],
                error_output_summary=f"Patch apply failed: {apply_result.get('error', 'unknown apply error')}",
                confidence_adjustment=-0.35,
                promotion_allowed=False,
            )
        validated_items.append("patch-apply")

        import_ok, import_message = self._run_import_validation(
            workspace_root=workspace_root,
            target_file=proposal.target_file,
            candidate_content=None,
        )
        if not import_ok:
            rollback_patch(workspace_root=workspace_root, patch=patch_payload)
            return RepairValidationResult(
                passed=False,
                validated_items=validated_items + ["import-load"],
                error_output_summary=import_message,
                confidence_adjustment=-0.3,
                promotion_allowed=False,
                applied_patch=True,
                rollback_performed=True,
            )
        validated_items.append("import-load")

        if proposal.validation_plan.targeted_tests:
            tests_ok, tests_message = self._run_targeted_tests(
                workspace_root=workspace_root,
                targeted_tests=proposal.validation_plan.targeted_tests,
            )
            if not tests_ok:
                rollback_patch(workspace_root=workspace_root, patch=patch_payload)
                return RepairValidationResult(
                    passed=False,
                    validated_items=validated_items + ["targeted-tests"],
                    error_output_summary=tests_message,
                    confidence_adjustment=-0.3,
                    promotion_allowed=False,
                    applied_patch=True,
                    rollback_performed=True,
                )
            validated_items.append("targeted-tests")

        return RepairValidationResult(
            passed=True,
            validated_items=validated_items,
            error_output_summary="Repair validation passed and promotion is allowed.",
            confidence_adjustment=0.15,
            promotion_allowed=True,
            applied_patch=True,
            rollback_performed=False,
        )

    def _receipt_smoke_check(self, *, proposal: RepairProposal) -> tuple[bool, str]:
        new_content = str(proposal.patch_payload.get("new_content", ""))
        if proposal.repair_strategy_class == "ensure_file_content_contract":
            return ('"content": content[:limit]' in new_content, "Repair smoke check failed: file.content contract was not restored.")
        if proposal.repair_strategy_class == "normalize_result_payload_shape":
            ok = "result_payload" in new_content and "_normalize_execution_callback_result" in new_content
            return (ok, "Repair smoke check failed: result payload normalizer was not present.")
        if proposal.repair_strategy_class == "normalize_error_payload_shape":
            return ("details" in new_content and "error_payload" in new_content, "Repair smoke check failed: error payload normalization was not present.")
        return (False, f"No receipt smoke check is defined for strategy {proposal.repair_strategy_class}.")

    def _run_import_validation(
        self,
        *,
        workspace_root: Path,
        target_file: str,
        candidate_content: str | None,
    ) -> tuple[bool, str]:
        target_path = workspace_root / target_file
        if candidate_content is None:
            file_to_load = target_path
            return self._execute_import_probe(workspace_root=workspace_root, file_to_load=file_to_load)
        temp_root = workspace_root / ".logs" / "self-repair-validation"
        temp_root.mkdir(parents=True, exist_ok=True)
        temp_dir = temp_root / f"import-{uuid4().hex[:8]}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_file = temp_dir / Path(target_file).name
        temp_file.write_text(candidate_content, encoding="utf-8")
        return self._execute_import_probe(workspace_root=workspace_root, file_to_load=temp_file)

    def _execute_import_probe(self, *, workspace_root: Path, file_to_load: Path) -> tuple[bool, str]:
        backend_python = workspace_root / "backend" / "python"
        script = (
            "import importlib.util, sys; "
            "sys.path.insert(0, sys.argv[1]); "
            "target = sys.argv[2]; "
            "spec = importlib.util.spec_from_file_location('omni_self_repair_validation', target); "
            "module = importlib.util.module_from_spec(spec); "
            "assert spec and spec.loader; "
            "spec.loader.exec_module(module); "
            "print('ok')"
        )
        completed = subprocess.run(
            [sys.executable, "-B", "-c", script, str(backend_python), str(file_to_load)],
            cwd=str(workspace_root),
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            return False, (completed.stderr or completed.stdout or "Import validation failed.").strip()
        return True, completed.stdout.strip() or "ok"

    def _run_targeted_tests(self, *, workspace_root: Path, targeted_tests: list[str]) -> tuple[bool, str]:
        existing_targets = [
            target for target in targeted_tests
            if (workspace_root / Path(*str(target).split("."))).with_suffix(".py").exists()
        ]
        if not existing_targets:
            return True, "targeted tests skipped because the mapped test modules are not present in this workspace"
        completed = subprocess.run(
            [sys.executable, "-m", "unittest", *existing_targets],
            cwd=str(workspace_root),
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            return False, (completed.stderr or completed.stdout or "Targeted tests failed.").strip()
        return True, completed.stdout.strip() or "targeted tests passed"
