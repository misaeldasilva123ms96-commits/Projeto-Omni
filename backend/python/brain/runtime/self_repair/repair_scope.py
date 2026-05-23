from __future__ import annotations

from pathlib import Path

from .models import RepairProposal, RepairScope, SelfRepairPolicy


class RepairScopeEnforcer:
    def evaluate(
        self,
        *,
        workspace_root: Path,
        proposal: RepairProposal,
        policy: SelfRepairPolicy,
    ) -> RepairScope:
        target_files = [proposal.target_file]
        if len(target_files) > policy.max_files:
            return RepairScope(
                mutation_type="single_file_runtime_patch",
                target_files=target_files,
                allowed_root=policy.allowed_root,
                max_files=policy.max_files,
                max_attempts=policy.max_attempts_per_action,
                validation_required=True,
                within_scope=False,
                reason_code="max_files_exceeded",
                summary="Repair proposal exceeds the maximum number of files allowed in this phase.",
            )

        target_path = (workspace_root / proposal.target_file).resolve()
        allowed_root = (workspace_root / policy.allowed_root).resolve()
        if not str(target_path).startswith(str(allowed_root)):
            return RepairScope(
                mutation_type="single_file_runtime_patch",
                target_files=target_files,
                allowed_root=policy.allowed_root,
                max_files=policy.max_files,
                max_attempts=policy.max_attempts_per_action,
                validation_required=True,
                within_scope=False,
                reason_code="target_outside_allowed_root",
                summary="Repair target is outside the approved runtime repair boundary.",
            )

        if not self._matches_allowed_targets(proposal.target_file, policy.allowed_targets):
            return RepairScope(
                mutation_type="single_file_runtime_patch",
                target_files=target_files,
                allowed_root=policy.allowed_root,
                max_files=policy.max_files,
                max_attempts=policy.max_attempts_per_action,
                validation_required=True,
                within_scope=False,
                reason_code="target_not_allowlisted",
                summary="Repair target is not allowlisted for Phase 15.",
            )

        return RepairScope(
            mutation_type="single_file_runtime_patch",
            target_files=target_files,
            allowed_root=policy.allowed_root,
            max_files=policy.max_files,
            max_attempts=policy.max_attempts_per_action,
            validation_required=True,
            within_scope=True,
            reason_code="within_scope",
            summary="Repair proposal is within the approved bounded mutation scope.",
        )

    def _matches_allowed_targets(self, target_file: str, patterns: list[str]) -> bool:
        target = target_file.replace("\\", "/")
        for pattern in patterns:
            normalized = pattern.replace("\\", "/")
            if "*" in normalized:
                if Path(target).match(normalized):
                    return True
                continue
            if target == normalized:
                return True
        return False
