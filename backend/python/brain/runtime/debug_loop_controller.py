from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from brain.runtime.engineering_tools import execute_engineering_action
from brain.runtime.patch_generator import apply_patch, build_patch, review_patch_risk, rollback_patch
from brain.runtime.workspace_manager import WorkspaceManager


class DebugLoopController:
    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.resolve()
        self.workspace_manager = WorkspaceManager(self.workspace_root)

    def run(
        self,
        *,
        task_message: str,
        test_command: Any = None,
        max_iterations: int = 2,
        repository_analysis: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        patch_history: list[dict[str, Any]] = []
        patch_sets: list[dict[str, Any]] = []
        debug_iterations: list[dict[str, Any]] = []
        last_test_result: dict[str, Any] | None = None

        for iteration in range(1, max_iterations + 1):
            test_result = execute_engineering_action(
                project_root=self.workspace_root,
                action={
                    "selected_tool": "test_runner",
                    "tool_arguments": {
                        "workspace_root": str(self.workspace_root),
                        "command": test_command,
                    },
                },
                timeout_seconds=120,
            )
            last_test_result = test_result
            payload = test_result.get("result_payload", {}) if isinstance(test_result, dict) else {}
            if test_result.get("ok"):
                debug_iterations.append(
                    {
                        "iteration": iteration,
                        "status": "tests_passed",
                        "test_result": payload,
                    }
                )
                return {
                    "status": "success",
                    "iterations": debug_iterations,
                    "patch_history": patch_history,
                    "patch_sets": patch_sets,
                    "test_results": payload,
                    "verification_summary": {"ok": True, "runs": [{"mode": "debug-loop-final-tests", "status": "passed", "result": payload}]},
                    "repository_analysis": repository_analysis or {},
                    "workspace_state": self.workspace_manager.snapshot_workspace(self.workspace_root),
                }

            patch = self._propose_fix(
                task_message=task_message,
                failure_output=f"{payload.get('stdout', '')}\n{payload.get('stderr', '')}",
                repository_analysis=repository_analysis or {},
            )
            if not patch:
                debug_iterations.append(
                    {
                        "iteration": iteration,
                        "status": "no_fix_found",
                        "test_result": payload,
                    }
                )
                break

            review = review_patch_risk(patch=patch)
            if not review.get("accepted"):
                debug_iterations.append(
                    {
                        "iteration": iteration,
                        "status": "review_blocked",
                        "warnings": review.get("warnings", []),
                        "test_result": payload,
                    }
                )
                break

            apply_result = apply_patch(workspace_root=self.workspace_root, patch=patch)
            if not apply_result.get("ok"):
                debug_iterations.append(
                    {
                        "iteration": iteration,
                        "status": "apply_failed",
                        "apply_result": apply_result,
                        "test_result": payload,
                    }
                )
                break

            patch_history.append(
                {
                    "iteration": iteration,
                    "patch": {
                        "file_path": patch.get("file_path"),
                        "patch_diff": patch.get("patch_diff"),
                        "confidence_score": patch.get("confidence_score"),
                    },
                    "review": review,
                }
            )
            patch_sets.append(
                {
                    "patch_set_id": f"debug-loop-{iteration}",
                    "affected_files": [patch.get("file_path")],
                    "dependency_notes": [],
                    "risk_level": review.get("risk_level", "low"),
                    "verification_plan": {"mode": "debug-loop"},
                }
            )

            verify_result = execute_engineering_action(
                project_root=self.workspace_root,
                action={
                    "selected_tool": "test_runner",
                    "tool_arguments": {
                        "workspace_root": str(self.workspace_root),
                        "command": test_command,
                    },
                },
                timeout_seconds=120,
            )
            verify_payload = verify_result.get("result_payload", {}) if isinstance(verify_result, dict) else {}
            debug_iterations.append(
                {
                    "iteration": iteration,
                    "status": "patched_and_verified" if verify_result.get("ok") else "patched_but_failed",
                    "test_result": verify_payload,
                    "patch_file": patch.get("file_path"),
                }
            )
            if verify_result.get("ok"):
                return {
                    "status": "success",
                    "iterations": debug_iterations,
                    "patch_history": patch_history,
                    "patch_sets": patch_sets,
                    "test_results": verify_payload,
                    "verification_summary": {"ok": True, "runs": [{"mode": "debug-loop-final-tests", "status": "passed", "result": verify_payload}]},
                    "repository_analysis": repository_analysis or {},
                    "workspace_state": self.workspace_manager.snapshot_workspace(self.workspace_root),
                }

            rollback_patch(workspace_root=self.workspace_root, patch=patch)

        return {
            "status": "failed",
            "iterations": debug_iterations,
            "patch_history": patch_history,
            "patch_sets": patch_sets,
            "test_results": (last_test_result or {}).get("result_payload", {}),
            "verification_summary": {"ok": False, "runs": [{"mode": "debug-loop-final-tests", "status": "failed", "result": (last_test_result or {}).get("result_payload", {})}]},
            "repository_analysis": repository_analysis or {},
            "workspace_state": self.workspace_manager.snapshot_workspace(self.workspace_root),
        }

    def _propose_fix(
        self,
        *,
        task_message: str,
        failure_output: str,
        repository_analysis: dict[str, Any],
    ) -> dict[str, Any] | None:
        candidates = [
            item.get("path")
            for item in repository_analysis.get("file_index", [])
            if isinstance(item, dict) and str(item.get("path", "")).endswith(".py") and "/tests/" not in str(item.get("path", ""))
        ]
        if not candidates:
            candidates = [
                str(path.relative_to(self.workspace_root)).replace("\\", "/")
                for path in self.workspace_root.rglob("*.py")
                if "/tests/" not in str(path.relative_to(self.workspace_root)).replace("\\", "/")
            ]

        for candidate in candidates:
            target = (self.workspace_root / candidate).resolve()
            if not target.exists():
                continue
            content = target.read_text(encoding="utf-8")
            new_content = self._attempt_python_operator_fix(content, failure_output, task_message)
            if new_content and new_content != content:
                return build_patch(
                    workspace_root=self.workspace_root,
                    file_path=candidate,
                    new_content=new_content,
                    confidence_score=0.82,
                )
        return None

    @staticmethod
    def _attempt_python_operator_fix(content: str, failure_output: str, task_message: str) -> str | None:
        lowered = failure_output.lower()
        if "assert" not in lowered and "failed" not in lowered:
            return None
        patterns = [
            (r"return\s+([A-Za-z_][A-Za-z0-9_]*)\s*-\s*([A-Za-z_][A-Za-z0-9_]*)", r"return \1 + \2"),
            (r"return\s+([A-Za-z_][A-Za-z0-9_]*)\s*\+\s*([A-Za-z_][A-Za-z0-9_]*)", r"return \1 - \2"),
        ]
        for index, (pattern, replacement) in enumerate(patterns):
            if re.search(pattern, content) and ("fix" in task_message.lower() or "corr" in task_message.lower() or "assert" in lowered):
                candidate = re.sub(pattern, replacement, content, count=1)
                if candidate != content:
                    return candidate
        return None
